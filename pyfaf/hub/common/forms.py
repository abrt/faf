from django import forms
from django.template.defaultfilters import slugify

from pyfaf.storage import OpSysRelease, OpSys
from pyfaf.hub.common.queries import (components_list,
                                      distro_release_id)
from pyfaf.hub.common.utils import split_distro_release, unique

class OsComponentFilterForm(forms.Form):
    os_release = forms.ChoiceField(label='OS', required=False)
    component = forms.ChoiceField(label='Components')

    def slugify(self, val):
        return val.lower().replace(' ', '-')

    def __init__(self, db, request):
        '''
        Builds choices according to user selection.
        '''

        self.db = db
        super(OsComponentFilterForm, self).__init__()
        self.os_releases = {}
        self.os_ids = {}
        self.fields['os_release'].choices = []

        self.fields['os_release'].widget.attrs['onchange'] = (
            'Dajaxice.pyfaf.hub.services.components(Dajax.process'
            ',{"os_release":this.value})')

        for distro in db.session.query(OpSys.name).all():
            releases = (db.session.query(OpSysRelease.id,
                OpSysRelease.version)
                .join(OpSys)
                .filter(OpSys.name == distro.name)
                .all())

            self.os_releases[distro.name] = releases

            all_str = 'All %s Releases' % distro.name
            self.fields['os_release'].choices.append((
                self.slugify(distro.name), all_str))

            all_releases = []
            for os in releases:
                key = self.slugify('%s %s' % (distro.name, os[1]))
                value = '%s %s' % (distro.name, os[1])
                all_releases.append(([os.id], value))
                self.os_ids[key]  = [([os.id], value)]
                self.fields['os_release'].choices.append((key, value))

            self.os_ids[self.slugify(distro.name)] = [(
                [x[0] for x in releases], all_str)] + all_releases

        # Set initial value for operating system release.
        self.fields['os_release'].initial = \
            self.fields['os_release'].choices[0][0]

        if 'os_release' in request:
            if request['os_release'] in self.os_ids.keys():
                self.fields['os_release'].initial = request['os_release']

        # Find all components
        self.os_rel = self.fields['os_release'].initial
        self.distro, self.release = split_distro_release(self.os_rel)
        self.os_release_id = distro_release_id(db, self.distro, self.release)

        self.component_list = components_list(db, [self.os_release_id]
            if self.os_release_id != -1 else [])

        self.fields['component'].choices = [('*', 'All Components')]
        comp_keys = []
        for comp in unique(self.component_list, lambda x: x[1]):
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
        return self.os_ids[self.os_rel]

    def get_component_selection(self):
        '''
        Returns list of IDs of selected components.
        Empty list means all components (no component filtering).
        '''
        name = self.fields['component'].initial
        if name == '*':
            return []

        component_ids = []
        for comp in self.component_list:
            if slugify(comp[1]) == name:
                component_ids.append(comp[0])

        return component_ids


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
