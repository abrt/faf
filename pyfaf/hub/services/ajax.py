from django.template.defaultfilters import slugify

from dajax.core import Dajax
from dajaxice.decorators import dajaxice_register

import pyfaf
from pyfaf.hub.common.queries import (components_list,
                                      distro_release_id,
                                      associates_list)
from pyfaf.hub.common.utils import split_distro_release, unique

@dajaxice_register
def components(request, os_release, associate, component_field):
    dajax = Dajax()

    db = pyfaf.storage.getDatabase()

    os_releases = []
    os_release_id = distro_release_id(db, *split_distro_release(os_release))
    if os_release_id != -1:
        os_releases.append(os_release_id)

    out = "<option value='*'>All Components</option>"
    for component in unique(components_list(db, os_releases,
                            None if '*' == associate else [int(associate)]), lambda x: x[1]):
        out += "<option value='%s'>%s</option>\n" % (slugify(component[1]), component[1])

    dajax.assign('#id_%s' % (component_field), 'innerHTML', out)
    return dajax.json()

@dajaxice_register
def associates(request, os_release, field):
    dajax = Dajax()

    db = pyfaf.storage.getDatabase()

    os_releases = None
    os_release_id = distro_release_id(db, *split_distro_release(os_release))
    if os_release_id != -1:
        os_releases = [os_release_id]

    out = "<option value='*'>All Associates</option>"
    for associate in associates_list(db, os_releases):
        out += "<option value='%s'>%s</option>\n" % (str(associate.id), associate.name)

    dajax.assign('#id_%s' % (field), 'innerHTML', out)
    return dajax.json()
