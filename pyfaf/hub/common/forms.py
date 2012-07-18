from django import forms
from django.utils.safestring import mark_safe
from django.template.defaultfilters import slugify

from pyfaf.storage import OpSysRelease, OpSys
from pyfaf.hub.common.queries import (components_list,
                                      distro_release_id,
                                      all_distros_with_all_releases)
from pyfaf.hub.common.utils import split_distro_release, unique

class FafChoiceField(forms.ChoiceField):
    def __init__(self, *args, **kwargs):
        super(FafChoiceField, self).__init__(*args, **kwargs)

    def try_to_select(self, value):
        if value in (idv for idv, plh in self.choices):
            self.initial = value

class OsReleaseField(FafChoiceField):
    def __init__(self, *args, **kwargs):
        super(OsReleaseField, self).__init__(*args, **kwargs)

    def slugify(self, val):
        return val.lower().replace(' ', '-')

    def populate_choices(self, distro_releases):
        self.choices=[('*', 'All Distributions')]
        self.initial = self.choices[0][0]
        self.all_os_ids = []
        self.os_ids = {}

        for distro, releases in distro_releases:
            all_str = 'All %s Releases' % distro.name
            self.choices.append((self.slugify(distro.name), all_str))

            all_releases = []
            self.all_os_ids.append(([x[0] for x in releases], all_str))

            for os in releases:
                key = self.slugify('%s %s' % (distro.name, os[1]))
                value = '%s %s' % (distro.name, os[1])
                all_releases.append(([os.id], value))
                self.os_ids[key]  = [([os.id], value)]
                self.all_os_ids.append(([os.id], value))
                self.choices.append((key,
                    mark_safe('&nbsp;'*6 + value)))

            self.os_ids[self.slugify(distro.name)] = [(
                [x[0] for x in releases], all_str)] + all_releases

        self.choices = self.choices

    def get_selection(self):
        if self.initial == '*':
            return self.all_os_ids
        return self.os_ids[self.initial]

class ComponentField(FafChoiceField):
    def __init__(self, *args, **kwargs):
        super(ComponentField, self).__init__(*args, **kwargs)

    def populate_choices(self, component_list):
        self.choices = [('*', 'All Components')]
        self.component_list = component_list
        for comp in unique(self.component_list, lambda x: x[1]):
            name = comp[1]
            self.choices.append((slugify(name), name))

        self.initial = self.choices[0][0]

    def get_selection(self):
        name = self.initial
        if name == '*':
            return []

        component_ids = []
        for comp in self.component_list:
            if slugify(comp[1]) == name:
                component_ids.append(comp[0])

        return component_ids

class OsComponentFilterForm(forms.Form):
    os_release = OsReleaseField(label='OS', required=False)
    component = ComponentField(label='Components')

    def __init__(self, db, request):
        '''
        Builds choices according to user selection.
        '''

        self.db = db
        super(OsComponentFilterForm, self).__init__()

        self.fields['os_release'].populate_choices(all_distros_with_all_releases(db))
        self.fields['os_release'].widget.attrs['onchange'] = (
            'Dajaxice.pyfaf.hub.services.components(Dajax.process'
            ',{"os_release":this.value,"component_field":"component"})')

        # Set initial value for operating system release.
        if 'os_release' in request:
            self.fields['os_release'].try_to_select(request['os_release'])

        # Find all components
        distro, release = split_distro_release(self.fields['os_release'].initial)
        self.os_release_id = distro_release_id(db, distro, release)

        self.fields['component'].populate_choices(components_list(db, [self.os_release_id]
            if self.os_release_id != -1 else []))

        if 'component' in request:
            self.fields['component'].try_to_select(request['component'])

    def get_release_selection(self):
        '''
        Returns list of IDs of selected OS releases and their names.
        Each ID is stored as a list instead of a single value.
        '''
        return self.fields['os_release'].get_selection()

    def get_component_selection(self):
        '''
        Returns list of IDs of selected components.
        Empty list means all components (no component filtering).
        '''
        return self.fields['component'].get_selection()



DEFAULT_CHOICES = (
    ('d', '14 days'),
    ('w', '8 weeks'),
    ('m', '12 months'),
    ('*', 'Server lifetime'),
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
