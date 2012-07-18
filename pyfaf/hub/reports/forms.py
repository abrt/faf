import json

from django import forms

from pyfaf import ureport
from pyfaf.hub.common.forms import (OsComponentFilterForm,
                                    DurationOsComponentFilterForm,
                                    FafMultipleChoiceField)

class ReportFilterForm(OsComponentFilterForm):
    status_values = ['new', 'fixed']
    # TODO : https://github.com/twitter/bootstrap/pull/2007
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

class ReportOverviewForm(DurationOsComponentFilterForm):
    graph_type = forms.ChoiceField(label='Type',
        choices=[('abs', 'Absolute'), ('rel', 'Relative')])

    def __init__(self, db, request):
        '''
        Add graph type selection to OsComponentFilterForm
        '''
        super(ReportOverviewForm, self).__init__(db, request,
                                                    [('m', 'months'),
                                                     ('w', 'weeks')])

        # Set initial value for graph_type.
        self.fields['graph_type'].initial = \
            self.fields['graph_type'].choices[0][0]

        if ('graph_type' in request and
            request['graph_type'] in
            (x[0] for x in self.fields['graph_type'].choices)):
            self.fields['graph_type'].initial = request['graph_type']

    def get_graph_type_selection(self):
        return self.fields['graph_type'].initial

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
