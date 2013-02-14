import os
import re
import rpm
import time
import logging
import datetime
import traceback
import subprocess

from rpmUtils import miscutils as rpmutils

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

def daterange(a_date, b_date, step=1, desc=False):
    '''
    Generator returning dates from lower to higher
    date if `desc` is False or from higher to lower
    if `desc` is True.

    `a_date` and `b_date` are always included in the
    result.
    '''

    lower = min(a_date, b_date)
    higher = max(a_date, b_date)

    if desc:
        for x in range(0, (higher - lower).days, step):
            dt = higher - datetime.timedelta(x)
            yield dt

        yield lower
    else:
        for x in range(0, (higher - lower).days, step):
            dt = lower + datetime.timedelta(x)
            yield dt

        yield higher


# Modified retry decorator with exponential backoff from PythonDecoratorLibrary
def retry(tries, delay=3, backoff=2, verbose=False):
    '''
    Retries a function or method until it returns value.

    Delay sets the initial delay in seconds, and backoff sets the factor by which
    the delay should lengthen after each failure. backoff must be greater than 1,
    or else it isn't really a backoff. tries must be at least 0, and delay
    greater than 0.
    '''

    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay # make mutable
            exception = None

            while mtries > 0:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    exception = e
                    if verbose:
                        print('Exception occured, retrying in {0} seconds'
                            ' {1}/{2}'.format(mdelay, (tries-mtries+1), tries))
                        msg = traceback.format_exception_only(type(exception),
                                exception)

                        if type(msg) == list:
                            msg = ''.join(msg)

                        print('Exception was: {0}'.format(msg))
                    mtries -= 1

                time.sleep(mdelay)
                mdelay *= backoff  # make future wait longer

            raise e # out of tries

        return f_retry
    return deco_retry
