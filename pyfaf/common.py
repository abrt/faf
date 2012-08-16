import os
import rpm
import logging
import rpmUtils

from pyfaf.storage.opsys import PackageDependency

def get_libname(path):
    libname = os.path.basename(path)
    idx = libname.rfind(".so")
    if idx > 0:
        libname = libname[0:idx + 3]
    return libname

def store_package_deps(db, package_obj):
    pkg_id = package_obj.id
    ts = rpm.ts()
    rpm_file = package_obj.get_lob_fd("package")
    header = ts.hdrFromFdno(rpm_file.fileno())

    files = header.fiFromHeader()
    logging.debug("Contains {0} files".format(len(files)))
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
            new.epoch, new.version, new.release = rpmUtils.miscutils.stringToVersion(evr)
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
            new.epoch, new.version, new.release = rpmUtils.miscutils.stringToVersion(evr)
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
            new.epoch, new.version, new.release = rpmUtils.miscutils.stringToVersion(evr)
        db.session.add(new)

    rpm_file.close()
    db.session.flush()
