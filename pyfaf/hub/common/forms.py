from django import forms
from django.template.defaultfilters import slugify

from pyfaf.storage import OpSysComponent, OpSysRelease, OpSys, Report

class OsComponentFilterForm(forms.Form):
    os_release = forms.ChoiceField(label='OS', required=False)
    component = forms.ChoiceField(label='Components')

    def __init__(self, db, request):
        '''
        Builds choices according to user selection.
        '''

        self.db = db
        super(OsComponentFilterForm, self).__init__()

        # TODO: Find all operating system releases
        distro = 'Fedora'
        releases = ['devel', '17', '16', '15']

        self.os_list = (db.session.query(OpSysRelease.id, OpSysRelease.version).
            join(OpSys).
            filter((OpSys.name == distro) &
                (OpSysRelease.version.in_(releases)))
            .all())

        self.fields['os_release'].choices = [(slugify(distro),
            'All %s Releases' % distro)]
        os_keys = []
        for os in self.os_list:
            key = slugify('%s %s' % (distro, os[1]))
            value = '%s %s' % (distro, os[1])
            os_keys.append(key)
            self.fields['os_release'].choices.append((key, value))


        # Set initial value for operating system release.
        self.fields['os_release'].initial = \
            self.fields['os_release'].choices[0][0]

        if 'os_release' in request:
            if request['os_release'] in os_keys:
                self.fields['os_release'].initial = request['os_release']

        # Find all components
        os_rel = self.fields['os_release'].initial
        self.distro, self.release = self.split_distro_release(os_rel)
        self.os_release_id = self.distro_release_id(self.distro, self.release)

        self.component_list = (
            db.session.query(OpSysComponent.id, OpSysComponent.name).
            join(OpSysComponent.opsysreleases, Report).
            filter((OpSysRelease.id == self.os_release_id) |
                (self.os_release_id == -1)).
            filter(OpSysComponent.id == Report.component_id).
            order_by(OpSysComponent.name).
            distinct(OpSysComponent.name).
            all())

        self.fields['component'].choices = [('*', 'All Components')]
        comp_keys = []
        for comp in self.component_list:
            name = comp[1]
            slug = slugify(comp[1])
            comp_keys.append(slug)
            self.fields['component'].choices.append((slug, name))

        self.fields['component'].initial = \
            self.fields['component'].choices[0][0]

        if 'component' in request:
            if request['component'] in comp_keys:
                self.fields['component'].initial = request['component']

    def get_release_selection(self):
        '''
        Returns list of IDs of selected OS releases and their names.
        Each ID is stored as a list instead of a single value.
        '''
        ids = [-1]
        names = ['All %s releases' % self.distro.capitalize()]
        for os in self.os_list:
            ids.append(os.id)
            names.append('%s %s' % (self.distro.capitalize(), os.version))

        oldids = [ os_id for os_id in ids]
        allids = oldids[1:]
        ids = [[os_id] for os_id in ids]
        ids[0] = allids
        names = [ os_name for os_name in names]
        if self.os_release_id != -1:
            ids = [[self.os_release_id]]
            names = [names[oldids.index(ids[0][0])]]

        return zip(ids, names)

    def get_component_selection(self):
        '''
        Returns list of IDs of selected components.
        Empty list means all components (no component filtering).
        '''
        name = self.fields['component'].initial
        if name == '*':
            return []

        component_id = None
        for comp in self.component_list:
            if slugify(comp[1]) == name:
                component_id = comp[0]
                break

        if component_id is None:
            return []

        return [component_id]

    def distro_release_id(self, distro, release):
        '''
        Returns ID of release based on distro name and release name.

        Returns -1 if distro is equal to release meaning all releases.
        '''
        if release == distro.lower():
            return -1

        query = (self.db.session.query(OpSysRelease.id).
            join(OpSys).
            filter((OpSys.name == distro.capitalize()) &
                (OpSysRelease.version == release))
            .first())

        if query is not None:
            return query[0]

        return None

    @staticmethod
    def split_distro_release(inp):
        '''
        Returns decomposed distro, release names.

        fedora results in (fedora, fedora) meaning all releases,
        fedora-17 results in (fedora, 17).
        '''
        distro = release = inp
        if '-' in inp:
            split = inp.split('-')
            distro = split[0]
            release = ''.join(split[1:])

        return (distro, release)


DEFAULT_CHOICES = (
    ('d', '14 days'),
    ('w', '8 weeks'),
    ('m', '12 months')
)

class DurationOsComponentFilterForm(OsComponentFilterForm):
    duration = forms.ChoiceField(choices=DEFAULT_CHOICES)

    def __init__(self, db, request, duration_choices=None):
        '''
        Add duration choices to OsComponentFilterForm.
        '''

        super(DurationOsComponentFilterForm, self).__init__(db, request)

        # Set duration choices.
        if duration_choices:
            self.fields['duration'].choices = duration_choices

        duration_choices = self.fields['duration'].choices
        # Set initial value for duration.
        if ('duration' in request and
                request['duration'] in (x[0] for x in duration_choices)):
            self.fields['duration'].initial = request['duration']
        else:
            self.fields['duration'].initial = duration_choices[0][0]

    def get_duration_selection(self):
        return self.fields['duration'].initial
