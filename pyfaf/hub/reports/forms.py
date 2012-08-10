import json

from django import forms

from pyfaf import ureport
from pyfaf.hub.common.forms import (OsComponentFilterForm,
                                    FafMultipleChoiceField)

class ReportFilterForm(OsComponentFilterForm):
    status_values = ['new', 'fixed']
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

    def clean_file(self):
        raw_data = self.cleaned_data['file'].read()

        try:
            data = json.loads(raw_data)
        except:
            raise forms.ValidationError('Invalid JSON file')

        converted = ureport.convert_to_str(data)
        try:
            ureport.validate(converted)
        except Exception as exp:
            raise forms.ValidationError('Validation failed: %s' % exp)

        return dict(converted=converted, json=raw_data)
