from django import forms
from ..common.forms import OsComponentFilterForm

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
