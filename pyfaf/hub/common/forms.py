import string

from django import forms

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
        distro = "Fedora";
        releases = ["devel","17","16","15"];

        os_list = db.session.query(OpSysRelease.id, OpSysRelease.version).join(OpSys).filter((OpSys.name == distro) & (OpSysRelease.version.in_(releases))).all()
        self.fields['os_release'].choices = [(-1,"All %s Releases" % (distro))] + [ (os[0], "%s %s" % (distro, string.replace(os[1],"devel","Rawhide"))) for os in os_list ]

        # Set initial value for operating system release.
        if 'os_release' in request and int(request['os_release']) in (x[0] for x in self.fields['os_release'].choices):
            self.fields['os_release'].initial = int(request['os_release'])
        else:
            self.fields['os_release'].initial = self.fields['os_release'].choices[0][0]

        # Find all components
        os_release_id=self.fields['os_release'].initial
        self.fields['component'].choices = [(-1, "All Components")]
        self.fields['component'].choices += db.session.query(OpSysComponent.id, OpSysComponent.name).\
            join(OpSysComponent.opsysreleases, Report).\
            filter((OpSysRelease.id == os_release_id) | (os_release_id == -1)).\
            filter(OpSysComponent.id == Report.component_id).\
            order_by(OpSysComponent.name).\
            distinct(OpSysComponent.name).\
            all()

        # Set initial value for component.
        if 'component' in request and int(request['component']) in (x[0] for x in self.fields['component'].choices):
            self.fields['component'].initial = int(request['component'])
        else:
            self.fields['component'].initial = self.fields['component'].choices[0][0]

    def get_releas_selection(self):
        """
        Returns select OS release IDs and their names. Each ID is stored as a list instead of a single value.
        """
        osrelease_id = self.fields['os_release'].initial
        ids, names = zip(*self.fields['os_release'].choices)
        oldids= [ os_id for os_id in ids]
        allids = oldids[1:]
        ids = [[os_id] for os_id in ids]
        ids[0]=allids
        names= [ os_name for os_name in names]
        if osrelease_id != -1:
            ids = [[osrelease_id]]
            names = [names[oldids.index(ids[0][0])]]

        return zip(ids,names)

    def get_component_selection(self):
        """
        Returns list of select component ids
        """
        if self.fields['component'].initial == -1:
            return []

        return [self.fields['component'].initial]

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
