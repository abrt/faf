import os
import re
import rpm
import logging
import rpmUtils
import subprocess

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
    logging.debug("{0} contains {1} files".format(package_obj.nvra(),
        len(files)))
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

userspace = re.compile('SIG[^)]+')

def format_reason(rtype, reason, function_name):
    if rtype == 'USERSPACE':
        res = userspace.search(reason)
        if res:
            return '{0} in {1}'.format(res.group(), function_name)

        return 'Crash in {0}'.format(function_name)

    if rtype == 'PYTHON':
        spl = reason.split(':')
        if spl >= 4:
            file, line, loc, exception = spl[:4]
            if loc == '<module>':
                loc = '{0}:{1}'.format(file, line)
            return '{0} in {1}'.format(exception, loc)

        return 'Exception'

    if rtype == 'KERNELOOPS':
        return 'Kerneloops'

    return 'Crash'

def cpp_demangle(mangled):
    cmd = ["c++filt", mangled]
    demangle_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout, stderr = demangle_proc.communicate()
    if demangle_proc.returncode != 0:
        logging.error('c++filt failed.'
            ' command {0} \n stdout: {1} \n stderr: {2} \n'.format(
            ' '.join(cmd), stdout, stderr))
        return None

    return stdout.strip()
