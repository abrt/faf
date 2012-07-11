import json

from django import forms

from pyfaf import ureport
from pyfaf.hub.common.forms import OsComponentFilterForm
from pyfaf.hub.common.forms import DurationOsComponentFilterForm

class ReportFilterForm(OsComponentFilterForm):
    status = forms.ChoiceField(label='Status',
        choices=[('new', 'NEW'), ('fixed', 'FIXED')])

    def __init__(self, db, request):
        '''
        Add status to OsComponentFilterForm
        '''
        super(ReportFilterForm, self).__init__(db, request)

        # Set initial value for status.
        self.fields['status'].initial = self.fields['status'].choices[0][0]
        if ('status' in request and
            request['status'] in
            (x[0] for x in self.fields['status'].choices)):
            self.fields['status'].initial = request['status']

    def get_status_selection(self):
        return self.fields['status'].initial

    def get_destination_selection(self):
        return self.fields['destination'].initial

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
