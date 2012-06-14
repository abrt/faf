from django.template.defaultfilters import slugify

from dajax.core import Dajax
from dajaxice.decorators import dajaxice_register

import pyfaf
from pyfaf.hub.common.queries import (components_list,
                                      distro_release_id)
from pyfaf.hub.common.utils import split_distro_release, unique

@dajaxice_register
def components(request, os_release):
    dajax = Dajax()

    db = pyfaf.storage.getDatabase()

    os_releases = []
    os_release_id = distro_release_id(db, *split_distro_release(os_release))
    if os_release_id != -1:
        os_releases.append(os_release_id)

    out = "<option value='*'>All Components</option>"
    for component in unique(components_list(db, os_releases), lambda x: x[1]):
        out += "<option value='%s'>%s</option>\n" % (slugify(component[1]), component[1])

    dajax.assign('#id_component', 'innerHTML', out)
    return dajax.json()
