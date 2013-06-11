# Copyright (C) 2013  ABRT Team
# Copyright (C) 2013  Red Hat, Inc.
#
# This file is part of faf.
#
# faf is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# faf is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with faf.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import

import rpm
import logging

from rpmUtils import miscutils as rpmutils

from pyfaf.storage.opsys import PackageDependency

__all__ = ["store_rpm_deps"]


def store_rpm_deps(db, package):
    """
    Save RPM dependencies of `package` to
    storage.

    Expects pyfaf.storage.opsys.Package object.
    """

    pkg_id = package.id
    ts = rpm.ts()
    rpm_file = package.get_lob_fd("package")
    if not rpm_file:
        logging.warning("Package {0} has no lob stored".format(package.name))
        return False

    header = ts.hdrFromFdno(rpm_file.fileno())

    files = header.fiFromHeader()
    logging.debug("{0} contains {1} files".format(package.nvra(),
                                                  len(files)))

    # Invalid name for type variable
    # pylint: disable-msg=C0103
    for f in files:
        new = PackageDependency()
        new.package_id = pkg_id
        new.type = "PROVIDES"
        new.name = f[0]
        new.flags = 0
        db.session.add(new)

    provides = header.dsFromHeader('providename')
    for p in provides:
        new = PackageDependency()
        new.package_id = pkg_id
        new.type = "PROVIDES"
        new.name = p.N()
        new.flags = p.Flags()
        evr = p.EVR()
        if len(evr):
            new.epoch, new.version, new.release = rpmutils.stringToVersion(evr)
        db.session.add(new)

    requires = header.dsFromHeader('requirename')
    for r in requires:
        new = PackageDependency()
        new.package_id = pkg_id
        new.type = "REQUIRES"
        new.name = r.N()
        new.flags = r.Flags()
        evr = r.EVR()
        if len(evr):
            new.epoch, new.version, new.release = rpmutils.stringToVersion(evr)
        db.session.add(new)

    conflicts = header.dsFromHeader('conflictname')
    for c in conflicts:
        new = PackageDependency()
        new.package_id = pkg_id
        new.type = "CONFLICTS"
        new.name = c.N()
        new.flags = c.Flags()
        evr = c.EVR()
        if len(evr):
            new.epoch, new.version, new.release = rpmutils.stringToVersion(evr)
        db.session.add(new)
    # pylint: enable-msg=C0103

    rpm_file.close()
    db.session.flush()
    return True
