import datetime
import json
import logging

from django import forms

from pyfaf import ureport
from pyfaf.hub.common.forms import (OsComponentFilterForm,
                                    FafMultipleChoiceField)
from pyfaf.storage import getDatabase, InvalidUReport

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

    def clean_file(self):
        raw_data = self.cleaned_data['file'].read()

        try:
            data = json.loads(raw_data)
        except Exception as ex:
            self._save_invalid_ureport(raw_data, str(ex))
            raise forms.ValidationError('Invalid JSON file')

        converted = ureport.convert_to_str(data)
        try:
            ureport.validate(converted)
        except Exception as exp:
            reporter = None
            if ("reporter" in converted and
                "name" in converted["reporter"] and
                "version" in converted["reporter"]):
                reporter = "{0} {1}".format(converted["reporter"]["name"],
                                            converted["reporter"]["version"])

            self._save_invalid_ureport(json.dumps(data, indent=2),
                                       str(exp), reporter=reporter)
            raise forms.ValidationError('Validation failed: %s' % exp)

        return dict(converted=converted, json=raw_data)

class NewAttachmentForm(forms.Form):
    file = forms.FileField(label='Attachment')

    def clean_file(self):
        raw_data = self.cleaned_data['file'].read()

        try:
            data = json.loads(raw_data)
        except:
            raise forms.ValidationError('Invalid JSON file')

        return dict(json=raw_data)
