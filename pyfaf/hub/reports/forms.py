from django import forms
from pyfaf.hub.common.forms import OsComponentFilterForm
from pyfaf.hub.common.forms import DurationOsComponentFilterForm

class ReportFilterForm(OsComponentFilterForm):
    destination = forms.ChoiceField(label="Destination", choices=[(0,"Red Hat Bugzilla"),(1,"KDE Bugtracking System")])
    status = forms.ChoiceField(label="Status", choices=[(0,"NEW"),(1,"FIXED")])

    def __init__(self, db, request):
        """
        request -- dictionary of request data
        """
        OsComponentFilterForm.__init__(self, db, request)

        # Set initial value for destination.
        if 'destination' in request and int(request['destination']) in (x[0] for x in self.fields['destination'].choices):
            self.fields['destination'].initial = int(request['destination'])
        else:
            self.fields['destination'].initial = self.fields['destination'].choices[0][0]

        # Set initial value for status.
        if 'status' in request and int(request['status']) in (x[0] for x in self.fields['status'].choices):
            self.fields['status'].initial = int(request['status'])
        else:
            self.fields['status'].initial = self.fields['status'].choices[0][0]

class ReportOverviewConfigurationForm(DurationOsComponentFilterForm):
    graph_type = forms.ChoiceField(label="Type", choices=[(0,"Absolute"),(1,"Relative")])

    def __init__(self, db, request):
        """
        request -- dictionary of request data
        """
        DurationOsComponentFilterForm.__init__(self, db, request, [("d","days"),("w","weeks"),("m","months")])

        # Set initial value for graph_type.
        if 'graph_type' in request and int(request['graph_type']) in (x[0] for x in self.fields['graph_type'].choices):
            self.fields['graph_type'].initial = int(request['graph_type'])
        else:
            self.fields['graph_type'].initial = self.fields['graph_type'].choices[0][0]
