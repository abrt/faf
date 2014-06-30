import datetime
import json
import logging

from django import forms

from pyfaf import ureport
from pyfaf.opsys import systems
from pyfaf.queries import get_unknown_opsys
from webfaf.common.forms import (OsComponentFilterForm,
                                 FafMultipleChoiceField)
from pyfaf.storage import getDatabase, InvalidUReport, UnknownOpSys

class ReportFilterForm(OsComponentFilterForm):
    status_values = ['new', 'processed']
    status = FafMultipleChoiceField(
                    label='Status',
                    choices=zip(status_values, map(lambda v: v.upper(), status_values)))

    def __init__(self, db, request):
        '''
        Add status to OsComponentFilterForm
        '''
        super(ReportFilterForm, self).__init__(db, request)

        # Set initial value for status.
        self.fields['status'].initial = ['new']
        if 'status' in request:
            self.fields['status'].try_to_select(request['status'])

    def get_status_selection(self):
        return self.fields['status'].initial

class NewReportForm(forms.Form):
    file = forms.FileField(label='uReport file')

    def _save_invalid_ureport(self, ureport, errormsg, reporter=None):
        try:
            db = getDatabase()

            new = InvalidUReport()
            new.errormsg = errormsg
            new.date = datetime.datetime.utcnow()
            new.reporter = reporter
            db.session.add(new)
            db.session.flush()

            new.save_lob("ureport", ureport)
        except Exception as ex:
            logging.error(str(ex))

    def _save_unknown_opsys(self, opsys):
        try:
            db = getDatabase()

            name = opsys.get("name")
            version = opsys.get("version")

            db_unknown_opsys = get_unknown_opsys(db, name, version)
            if db_unknown_opsys is None:
                db_unknown_opsys = UnknownOpSys()
                db_unknown_opsys.name = name
                db_unknown_opsys.version = version
                db_unknown_opsys.count = 0
                db.session.add(db_unknown_opsys)

            db_unknown_opsys.count += 1
            db.session.flush()
        except Exception as ex:
            logging.error(str(ex))

    def clean_file(self):
        raw_data = self.cleaned_data['file'].read()

        try:
            data = json.loads(raw_data)
        except Exception as ex:
            self._save_invalid_ureport(raw_data, str(ex))
            raise forms.ValidationError('Invalid JSON file')

        try:
            ureport.validate(data)
        except Exception as exp:
            reporter = None
            if ("reporter" in data and
                "name" in data["reporter"] and
                "version" in data["reporter"]):
                reporter = "{0} {1}".format(data["reporter"]["name"],
                                            data["reporter"]["version"])

            self._save_invalid_ureport(json.dumps(data, indent=2),
                                       str(exp), reporter=reporter)

            if ("os" in data and
                "name" in data["os"] and
                data["os"]["name"] not in systems and
                data["os"]["name"].lower() not in systems):
                self._save_unknown_opsys(data["os"])

            raise forms.ValidationError('Validation failed: %s' % exp)

        return dict(converted=data, json=raw_data)

class NewAttachmentForm(forms.Form):
    file = forms.FileField(label='Attachment')

    def clean_file(self):
        raw_data = self.cleaned_data['file'].read()

        try:
            data = json.loads(raw_data)
        except:
            raise forms.ValidationError('Invalid JSON file')

        try:
            ureport.validate_attachment(data)
        except Exception as ex:
            raise forms.ValidationError("Validation failed: %s" % ex)

        return dict(json=raw_data)
