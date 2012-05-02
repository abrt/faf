import json

from django import forms

from pyfaf import ureport
from pyfaf.hub.common.forms import OsComponentFilterForm
from pyfaf.hub.common.forms import DurationOsComponentFilterForm

class ReportFilterForm(OsComponentFilterForm):
    destination = forms.ChoiceField(label='Destination',
        choices=[
            ('rhbz', 'Red Hat Bugzilla'),
            ('kdebz', 'KDE Bugtracking System')
            ])
    status = forms.ChoiceField(label='Status',
        choices=[('new', 'NEW'), ('fixed', 'FIXED')])

    def __init__(self, db, request):
        '''
        Add destination and status to OsComponentFilterForm
        '''
        super(ReportFilterForm, self).__init__(db, request)

        # Set initial value for destination.
        self.fields['destination'].initial = \
            self.fields['destination'].choices[0][0]
        if ('destination' in request and
            request['destination'] in
            (x[0] for x in self.fields['destination'].choices)):
            self.fields['destination'].initial = request['destination']

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
        super(ReportOverviewForm, self).__init__(db, request)

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
    file = forms.FileField(label='JSON Report')

    def clean_file(self):
        raw_data = self.cleaned_data['file'].read()

        try:
            data = json.loads(raw_data)
        except:
            raise forms.ValidationError('Invalid JSON file')

        converted = ureport.convert_to_str(data)
        try:
            ureport.validate(converted)
        except:
            raise forms.ValidationError('Validation failed')

        return dict(converted=converted, json=raw_data)
