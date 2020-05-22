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

import os
import shutil
import tempfile
from subprocess import Popen, PIPE, TimeoutExpired
from typing import Optional, Tuple
import rpm
from pyfaf.common import FafError, log
from pyfaf.config import config
from pyfaf.storage.opsys import PackageDependency

log = log.getChild(__name__)

__all__ = ["store_rpm_deps", "unpack_rpm_to_tmp"]


# https://github.com/rpm-software-management/rpm/commit/be0c4b5dce1630637c98002730d840cd6806c370
# XXX: Once the code is available in a stable release, we should ditch this code.
def parse_evr(evr_string) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """
    Parse epoch:version-release according to rpmUtils.miscutils.stringToVersion()
    """

    if evr_string in [None, '']:
        return (None, None, None)

    if evr_string.find(':') > -1:
        epoch, evr_string = evr_string.split(":", 1)
        if epoch == '':
            epoch = 0
        # https://github.com/abrt/faf/issues/927
        elif epoch and not epoch.isnumeric():
            raise ValueError('EVR string contains a non-numeric epoch: {}'.format(epoch))
    else:
        epoch = 0
    if evr_string.find('-') > -1:
        version, release = evr_string.split("-", 1)
    else:
        version = evr_string
        release = None
    if version == '':
        version = None

    return (epoch, version, release)


def store_rpm_deps(db, package, nogpgcheck=False) -> bool:
    """
    Save RPM dependencies of `package` to
    storage.

    Expects pyfaf.storage.opsys.Package object.
    """

    pkg_id = package.id
    ts = rpm.ts()
    rpm_file = package.get_lob_fd("package")
    if not rpm_file:
        raise FafError("Package {0} has no lob stored".format(package.name))

    if nogpgcheck:
        ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES) #pylint: disable=protected-access

    try:
        header = ts.hdrFromFdno(rpm_file.fileno())
    except rpm.error as exc:
        rpm_file.close()
        raise FafError("rpm error: {0}".format(exc))

    files = header.fiFromHeader()
    log.debug("%s contains %d files", package.nvra(), len(files))

    db.session.begin_nested()

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
        if evr:
            try:
                new.epoch, new.version, new.release = parse_evr(evr)
            except ValueError as ex:
                rpm_file.close()
                db.session.rollback()
                raise FafError("Unparsable EVR in {} dependency {}: {}".format(package.name, p.N(), ex))
        db.session.add(new)

    requires = header.dsFromHeader('requirename')
    for r in requires:
        new = PackageDependency()
        new.package_id = pkg_id
        new.type = "REQUIRES"
        new.name = r.N()
        new.flags = r.Flags()
        evr = r.EVR()
        if evr:
            try:
                new.epoch, new.version, new.release = parse_evr(evr)
            except ValueError as ex:
                rpm_file.close()
                db.session.rollback()
                raise FafError("Unparsable EVR in {} dependency {}: {}".format(package.name, r.N(), ex))
        db.session.add(new)

    conflicts = header.dsFromHeader('conflictname')
    for c in conflicts:
        new = PackageDependency()
        new.package_id = pkg_id
        new.type = "CONFLICTS"
        new.name = c.N()
        new.flags = c.Flags()
        evr = c.EVR()
        if evr:
            try:
                new.epoch, new.version, new.release = parse_evr(evr)
            except ValueError as ex:
                rpm_file.close()
                db.session.rollback()
                raise FafError("Unparsable EVR in {} dependency {}: {}".format(package.name, c.N(), ex))
        db.session.add(new)
    # pylint: enable-msg=C0103

    rpm_file.close()
    db.session.flush()


def unpack_rpm_to_tmp(path, prefix="faf") -> str:
    """
    Unpack RPM package to a temp directory. The directory is either specified
    in storage.tmpdir config option or use the system default temp directory.
    """

    tmpdir = config.get("storage.tmpdir", None)

    result = tempfile.mkdtemp(prefix=prefix, dir=tmpdir)
    for dirname in ["bin", "lib", "lib64", "sbin"]:
        os.makedirs(os.path.join(result, "usr", dirname))
        os.symlink(os.path.join("usr", dirname), os.path.join(result, dirname))

    rpm2cpio = Popen(["rpm2cpio", path], stdout=PIPE, stderr=PIPE)
    cpio = Popen(["cpio", "-id", "--quiet"], stdin=rpm2cpio.stdout, stderr=PIPE, cwd=result)

    #FIXME: false positive by pylint # pylint: disable=fixme
    rpm2cpio.stdout.close() # pylint: disable=no-member
    try:
        # generous timeout of 15 minutes (kernel unpacking)
        cpio.communicate(timeout=900)
    except TimeoutExpired:
        cpio.kill()
        cpio.communicate()
    finally:
        if cpio.returncode != 0:
            shutil.rmtree(result)
            raise FafError("Failed to unpack RPM '{0}'".format(path))

    return result
