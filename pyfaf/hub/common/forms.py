from django import forms
from django.contrib import messages
from sqlalchemy import func
from pyfaf.storage import OpSysComponent, OpSysRelease, OpSys, Report

class OsComponentFilterForm(forms.Form):
    os_release = forms.ChoiceField(label="OS", required=False)
    component = forms.ChoiceField(label="Components")

    def __init__(self, db, request):
        """
        request -- dictionary of request data
        """
        forms.Form.__init__(self)

        # Find all operating system releases
        rawhide = db.session.query(OpSysRelease.id).join(OpSys).filter(OpSys.name == "Fedora", OpSysRelease.version == "devel").one()
        f17 = db.session.query(OpSysRelease.id).join(OpSys).filter(OpSys.name == "Fedora", OpSysRelease.version == "17").one()
        f16 = db.session.query(OpSysRelease.id).join(OpSys).filter(OpSys.name == "Fedora", OpSysRelease.version == "16").one()
        f15 = db.session.query(OpSysRelease.id).join(OpSys).filter(OpSys.name == "Fedora", OpSysRelease.version == "15").one()
        self.fields['os_release'].choices = [ (rawhide[0], "Fedora Rawhide"),
                                              (f17[0], "Fedora 17"),
                                              (f16[0], "Fedora 16"),
                                              (f15[0], "Fedora 15") ]

        # Set initial value for operating system release.
        if 'os_release' in request and int(request['os_release']) in (x[0] for x in self.fields['os_release'].choices):
            self.fields['os_release'].initial = int(request['os_release'])
        else:
            self.fields['os_release'].initial = f17[0]

        # Find all components
        self.fields['component'].choices = [(-1, "All Components")]
        self.fields['component'].choices += db.session.query(OpSysComponent.id, OpSysComponent.name).\
            join(OpSysComponent.opsysreleases, Report).\
            filter(OpSysRelease.id == self.fields['os_release'].initial,
                   OpSysComponent.id == Report.component_id).\
            order_by(OpSysComponent.name).\
            distinct(OpSysComponent.name).\
            all()

        # Set initial value for component.
        if 'component' in request and int(request['component']) in (x[0] for x in self.fields['component'].choices):
            self.fields['component'].initial = int(request['component'])
        else:
            self.fields['component'].initial = self.fields['component'].choices[0][0]


class DurationOsComponentFilterForm(OsComponentFilterForm):
    duration = forms.ChoiceField(choices=(("d", "14 days"), ("w", "8 weeks"), ("m", "12 months")))

    def __init__(self, db, request, duration_choices=None):
        """
        request -- dictionary of request data
        """
        OsComponentFilterForm.__init__(self, db, request)

        # Set duration choices.
        if duration_choices:
            self.fields['duration'].choices = duration_choices

        # Set initial value for duration.
        if 'duration' in request and request['duration'] in (x[0] for x in self.fields['duration'].choices):
            self.fields['duration'].initial = request['duration']
        else:
            self.fields['duration'].initial = self.fields['duration'].choices[0][0]
