#!/usr/bin/python

# The rpm module needs to be included before solv module, otherwise it
# crashes on usage. Even when rpm module is not used here, include it
# to avoid initialization problems.
import rpm
import solv

import os
import re
import sys
import stat
import time
import urllib2
import logging
import tempfile

from pyfaf import config
from pyfaf import storage
from pyfaf.storage.opsys import (Package,
                                 PackageDependency,
                                 OpSys,
                                 Tag,
                                 TagInheritance,
                                 Build)

class RpmSenseFlags(object):
    # Flags from RPM, not exported to Python
    RPMSENSE_ANY = 0
    RPMSENSE_LESS = (1 << 1)
    RPMSENSE_GREATER = (1 << 2)
    RPMSENSE_EQUAL = (1 << 3)
    RPMSENSE_PROVIDES = (1 << 4)
    RPMSENSE_CONFLICTS = (1 << 5)
    RPMSENSE_OBSOLETES = (1 << 7)
    RPMSENSE_INTERP = (1 << 8)
    RPMSENSE_SCRIPT_PRE = ((1 << 9)| RPMSENSE_ANY)
    RPMSENSE_SCRIPT_POST = ((1 << 10)| RPMSENSE_ANY)
    RPMSENSE_SCRIPT_PREUN = ((1 << 11)| RPMSENSE_ANY)
    RPMSENSE_SCRIPT_POSTUN = ((1 << 12)| RPMSENSE_ANY)
    RPMSENSE_SCRIPT_VERIFY = (1 << 13)
    RPMSENSE_FIND_REQUIRES = (1 << 14)
    RPMSENSE_FIND_PROVIDES = (1 << 15)
    RPMSENSE_TRIGGERIN = (1 << 16)
    RPMSENSE_TRIGGERUN = (1 << 17)
    RPMSENSE_TRIGGERPOSTUN = (1 << 18)
    RPMSENSE_MISSINGOK = (1 << 19)
    RPMSENSE_SCRIPT_PREP = (1 << 20)
    RPMSENSE_SCRIPT_BUILD = (1 << 21)
    RPMSENSE_SCRIPT_INSTALL = (1 << 22)
    RPMSENSE_SCRIPT_CLEAN = (1 << 23)
    RPMSENSE_RPMLIB = ((1 << 24) | RPMSENSE_ANY)
    RPMSENSE_TRIGGERPREIN = (1 << 25)
    RPMSENSE_KEYRING = (1 << 26)
    RPMSENSE_PATCHES = (1 << 27)
    RPMSENSE_CONFIG = (1 << 28)

class GenericRepo(dict):
    """
    A common parent to all types of repositories.
    The code is based on pysolv example from libsolv.
    """
    def __init__(self, name, type, md_cache_dir, attribs={}):
        for k in attribs:
            self[k] = attribs[k]
        self.name = name
        self.type = type
        self.md_cache_dir = md_cache_dir

    def cache_path(self, ext = None):
        path = re.sub(r'^\.', '_', self.name)
        if ext:
            path += "_" + ext + ".solvx"
        else:
            path += ".solv"
        return os.path.join(self.md_cache_dir, re.sub(r'[/]', '_', path))

    def load(self, pool):
        self.handle = pool.add_repo(self.name)
        self.handle.appdata = self
        self.handle.priority = 99 - self['priority']
        dorefresh = self['autorefresh']
        if dorefresh:
            try:
                st = os.stat(self.cache_path())
                if time.time() - st[stat.ST_MTIME] < self['metadata_expire']:
                    dorefresh = False
            except OSError, e:
                pass
        self['cookie'] = ''
        if not dorefresh and self.use_cached_repo(None):
            logging.info("Loading cached repository '{0}'.".format(self.name))
            return True
        if self["fail_nocache"]:
            raise Exception("There is no cached repository. "
                            "Consider running faf-refreshrepo.")
        return self.load_if_changed()

    def load_if_changed(self):
        return False

    def load_ext(self, repodata):
        return False

    def set_from_urls(self, urls):
        if not urls:
            return
        url = urls[0]
        mirror = re.sub(r'^(.*?/...*?)/.*$', r'\1', url)
        logging.info("  - using mirror {0}".format(mirror))
        self['baseurl'] = url

    def set_from_metalink(self, metalink):
        nf = self.download(metalink, False)
        if not nf:
            return None
        f = os.fdopen(os.dup(solv.xfileno(nf)), 'r')
        solv.xfclose(nf)
        urls = []
        chksums = []
        for l in f.readlines():
            l = l.strip()
            m = re.match(r'^https?://.+/', l)
            if m:
                urls.append(m.group(0))
            m = re.match(r'^<hash type="sha256">([0-9a-fA-F]{64})</hash>', l)
            if m:
                chksums.append(solv.Chksum(solv.REPOKEY_TYPE_SHA256, m.group(1)))
            m = re.match(r'^<url.*>(https?://.+)repodata/repomd.xml</url>', l)
            if m:
                urls.append(m.group(1))
        if len(urls) == 0:
            chksums = [] # in case the metalink is about a different file
        f.close()
        self.set_from_urls(urls)
        return chksums

    def set_from_mirror_list(self, mirrorlist):
        nf = self.download(mirrorlist, False)
        if not nf:
            return
        f = os.fdopen(os.dup(solv.xfileno(nf)), 'r')
        solv.xfclose(nf)
        urls = []
        for l in f.readline():
            l = l.strip()
            if l[0:6] == 'http://' or l[0:7] == 'https://':
                urls.append(l)
        self.set_from_urls(urls)
        f.close()

    def download(self, file, uncompress, chksums=[], markincomplete=False):
        url = None
        if 'baseurl' not in self:
            if 'metalink' in self:
                if file != self['metalink']:
                    metalinkchksums = self.set_from_metalink(self['metalink'])
                    if file == 'repodata/repomd.xml' and len(chksums) == 0:
                        chksums = metalinkchksums
                else:
                    url = file
            elif 'mirrorlist' in self:
                if file != self['mirrorlist']:
                    self.set_from_mirror_list(self['mirrorlist'])
                else:
                    url = file
        if not url:
            if 'baseurl' not in self:
                logging.error("Error: {0}: no baseurl".format(self.name))
                return None
            url = re.sub(r'/$', '', self['baseurl']) + '/' + file
        logging.info("  - downloading {0}".format(url))
        f = tempfile.TemporaryFile()
        try:
            urlfile = urllib2.urlopen(url, timeout=30)
            while True:
                data = urlfile.read(8*32168)
                if len(data) == 0:
                    break
                f.write(data)
            urlfile.close()
        except urllib2.URLError as e:
            logging.error("Error: {0}: download error: {1}".format(url, e))
            if markincomplete:
                self['incomplete'] = True
            return None
        f.flush()
        os.lseek(f.fileno(), 0, os.SEEK_SET)
        verified = (len(chksums) == 0)
        for chksum in chksums:
            fchksum = solv.Chksum(chksum.type)
            if fchksum is None:
                if markincomplete:
                    self['incomplete'] = True
                continue
            fchksum.add_fd(f.fileno())
            if fchksum.raw() != chksum.raw():
                if markincomplete:
                    self['incomplete'] = True
                continue
            else:
                verified = True
        if not verified:
            logging.error("Error {0}: checksum mismatch or unknown "
                          "checksum type".format(file))
            return None
        if uncompress:
            return solv.xfopen_fd(file, os.dup(f.fileno()))
        return solv.xfopen_fd(None, os.dup(f.fileno()))

    def use_cached_repo(self, ext, mark=False):
        if not ext:
            cookie = self['cookie']
        else:
            cookie = self['extcookie']
        try:
            repopath = self.cache_path(ext)
            f = open(repopath, 'r')
            f.seek(-32, os.SEEK_END)
            fcookie = f.read(32)
            if len(fcookie) != 32:
                return False
            if cookie and fcookie != cookie:
                return False
            if self.type != 'system' and not ext:
                f.seek(-32 * 2, os.SEEK_END)
                fextcookie = f.read(32)
                if len(fextcookie) != 32:
                    return False
            f.seek(0)
            flags = 0
            if ext:
                flags = solv.Repo.REPO_USE_LOADING | solv.Repo.REPO_EXTEND_SOLVABLES
                if ext != 'DL':
                    flags |= solv.Repo.REPO_LOCALPOOL
            if not self.handle.add_solv(f, flags):
                return False
            if self.type != 'system' and not ext:
                self['cookie'] = fcookie
                self['extcookie'] = fextcookie
            if mark:
                # no futimes in python?
                try:
                    os.utime(repopath, None)
                except Exception, e:
                    pass
        except IOError, e:
            return False
        return True

    def get_ext_cookie(self, f):
        chksum = solv.Chksum(solv.REPOKEY_TYPE_SHA256)
        chksum.add(self['cookie'])
        if f:
            st = os.fstat(f.fileno())
            chksum.add(str(st[stat.ST_DEV]))
            chksum.add(str(st[stat.ST_INO]))
            chksum.add(str(st[stat.ST_SIZE]))
            chksum.add(str(st[stat.ST_MTIME]))
        extcookie = chksum.raw()
        # compatibility to c code
        if ord(extcookie[0]) == 0:
            extcookie = chr(1) + extcookie[1:]
        self['extcookie'] = extcookie

    def write_cached_repo(self, ext, info=None):
        try:
            if not os.path.isdir(self.md_cache_dir):
                os.mkdir(self.md_cache_dir, 0755)
            (fd, tmpname) = tempfile.mkstemp(prefix='.newsolv-',
                                             dir=self.md_cache_dir)
            os.fchmod(fd, 0444)
            f = os.fdopen(fd, 'w+')
            if not info:
                self.handle.write(f)
            elif ext:
                info.write(f)
            else:       # rewrite_repos case
                self.handle.write_first_repodata(f)
            if self.type != 'system' and not ext:
                if 'extcookie' not in self:
                    self.get_ext_cookie(f)
                f.write(self['extcookie'])
            if not ext:
                f.write(self['cookie'])
            else:
                f.write(self['extcookie'])
            f.close()
            if self.handle.iscontiguous():
                # Switch to saved repo to activate paging and save memory.
                nf = solv.xfopen(tmpname)
                if not ext:
                    # Main repository.
                    self.handle.empty()
                    if not self.handle.add_solv(nf, solv.Repo.SOLV_ADD_NO_STUBS):
                        sys.exit("Internal error, cannot reload solv file.")
                else:
                    # Extension repodata.
                    # Need to extend to repo boundaries, as this is how
                    # info.write() has written the data.
                    info.extend_to_repo()
                    # LOCALPOOL does not help as pool already contains all ids
                    info.add_solv(nf, solv.Repo.REPO_EXTEND_SOLVABLES)
                solv.xfclose(nf)
            os.rename(tmpname, self.cache_path(ext))
        except IOError, e:
            if tmpname:
                os.unlink(tmpname)

    def update_added_provides(self, addedprovides):
        if 'incomplete' in self:
            return
        if 'handle' not in self:
            return
        if self.handle.isempty():
            return
        # Make sure there's just one real repodata with extensions.
        repodata = self.handle.first_repodata()
        if not repodata:
            return
        oldaddedprovides = repodata.lookup_idarray(solv.SOLVID_META,
                                                   solv.REPOSITORY_ADDEDFILEPROVIDES)
        if not set(addedprovides) <= set(oldaddedprovides):
            for id in addedprovides:
                repodata.add_idarray(solv.SOLVID_META,
                                     solv.REPOSITORY_ADDEDFILEPROVIDES, id)
            repodata.internalize()
            self.write_cached_repo(None, repodata)

class MetadataRepo(GenericRepo):
    """
    Repository with RPM metadata, such as common Fedora repositories.
    """

    def load_if_changed(self):
        logging.info("Checking rpmmd repo '{0}'.".format(self.name))
        sys.stdout.flush()
        f = self.download("repodata/repomd.xml", False)
        if not f:
            logging.info("  - no repomd.xml file, skipping")
            self.handle.free(True)
            del self.handle
            return False

        # Calculate a cookie from repomd contents.
        chksum = solv.Chksum(solv.REPOKEY_TYPE_SHA256)
        chksum.add_fp(f)
        self['cookie'] = chksum.raw()

        if self.use_cached_repo(None, True):
            logging.info("  - using cached metadata")
            solv.xfclose(f)
            return True
        os.lseek(solv.xfileno(f), 0, os.SEEK_SET)
        self.handle.add_repomdxml(f, 0)
        solv.xfclose(f)
        logging.info("  - fetching metadata")
        (filename, filechksum) = self.find('primary')
        if filename:
            f = self.download(filename, True, [filechksum], True)
            if f:
                self.handle.add_rpmmd(f, None, 0)
                solv.xfclose(f)
            if 'incomplete' in self:
                return False # Hopeless, need good primary.
        (filename, filechksum) = self.find('updateinfo')
        if filename:
            f = self.download(filename, True, [filechksum], True)
            if f:
                self.handle.add_updateinfoxml(f, 0)
                solv.xfclose(f)
        self.add_exts()
        if 'incomplete' not in self:
            self.write_cached_repo(None)
        # Must be called after writing the repo.
        self.handle.create_stubs()
        return True

    def find(self, what):
        di = self.handle.Dataiterator(solv.SOLVID_META,
                                      solv.REPOSITORY_REPOMD_TYPE, what,
                                      solv.Dataiterator.SEARCH_STRING)
        di.prepend_keyname(solv.REPOSITORY_REPOMD)
        for d in di:
            d.setpos_parent()
            filename = d.pool.lookup_str(solv.SOLVID_POS,
                                         solv.REPOSITORY_REPOMD_LOCATION)
            chksum = d.pool.lookup_checksum(solv.SOLVID_POS,
                                            solv.REPOSITORY_REPOMD_CHECKSUM)
            if filename and not chksum:
                logging.error("Error: no {0} file checksum!".format(filename))
                filename = None
                chksum = None
            if filename:
                return (filename, chksum)
        return (None, None)

    def add_ext(self, repodata, what, ext):
        filename, chksum = self.find(what)
        if not filename and what == 'deltainfo':
            filename, chksum = self.find('prestodelta')
        if not filename:
            return
        handle = repodata.new_handle()
        repodata.set_poolstr(handle, solv.REPOSITORY_REPOMD_TYPE, what)
        repodata.set_str(handle, solv.REPOSITORY_REPOMD_LOCATION, filename)
        repodata.set_checksum(handle, solv.REPOSITORY_REPOMD_CHECKSUM, chksum)
        if ext == 'DL':
            repodata.add_idarray(handle, solv.REPOSITORY_KEYS,
                                 solv.REPOSITORY_DELTAINFO)
            repodata.add_idarray(handle, solv.REPOSITORY_KEYS,
                                 solv.REPOKEY_TYPE_FLEXARRAY)
        elif ext == 'FL':
            repodata.add_idarray(handle, solv.REPOSITORY_KEYS,
                                 solv.SOLVABLE_FILELIST)
            repodata.add_idarray(handle, solv.REPOSITORY_KEYS,
                                 solv.REPOKEY_TYPE_DIRSTRARRAY)
        repodata.add_flexarray(solv.SOLVID_META, solv.REPOSITORY_EXTERNAL, handle)

    def add_exts(self):
        repodata = self.handle.add_repodata(0)
        self.add_ext(repodata, 'deltainfo', 'DL')
        self.add_ext(repodata, 'filelists', 'FL')
        repodata.internalize()

    def load_ext(self, repodata):
        repomdtype = repodata.lookup_str(solv.SOLVID_META,
                                         solv.REPOSITORY_REPOMD_TYPE)
        if repomdtype == 'filelists':
            ext = 'FL'
        elif repomdtype == 'deltainfo':
            ext = 'DL'
        else:
            return False
        logging.info("Loading extended metadata {1} for {0}.".format(
                self.name, repomdtype))
        if self.use_cached_repo(ext):
            logging.info("  - found recent copy in cache")
            return True
        logging.info("  - fetching")
        filename = repodata.lookup_str(solv.SOLVID_META,
                                       solv.REPOSITORY_REPOMD_LOCATION)
        filechksum = repodata.lookup_checksum(solv.SOLVID_META,
                                              solv.REPOSITORY_REPOMD_CHECKSUM)
        f = self.download(filename, True, [filechksum])
        if not f:
            return False
        if ext == 'FL':
            self.handle.add_rpmmd(f, 'FL', solv.Repo.REPO_USE_LOADING |
                                  solv.Repo.REPO_EXTEND_SOLVABLES)
        elif ext == 'DL':
            self.handle.add_deltainfoxml(f, solv.Repo.REPO_USE_LOADING)
        solv.xfclose(f)
        self.write_cached_repo(ext, repodata)
        return True

def inherit(session, tag):
    result = [tag]
    inhs = session.query(TagInheritance).filter(TagInheritance.tag_id == tag.id).all()
    for inh in sorted(inhs, key=lambda x: x.priority, reverse=True):
        result.extend(inherit(session, inh.parent))

    return result

class FafStorageRepo(GenericRepo):
    """
    Repository based on Faf storage tables.
    """

    def __init__(self, os, tag, md_cache_dir=None, session=None, attribs={}):
        """
        session - database session
        """
        if md_cache_dir is None:
            md_cache_dir = config.CONFIG["llvmbuild.repodir"]

        self.session = storage.getDatabase().session if session is None else session
        self.os = self.session.query(OpSys).filter(OpSys.name == os).first()
        self.tag = self.session.query(Tag).filter(Tag.opsys_id == self.os.id).filter(Tag.name == tag).first()

        GenericRepo.__init__(self,
                             name="libsolv-{0}-{1}".format(os, tag),
                             type="faf-storage",
                             md_cache_dir=md_cache_dir,
                             attribs=attribs)

    def pass_data_to_handler(self):
        data = self.handle.add_repodata(0)
        pool = self.handle.pool

        logging.info("Preparing a list of packages")
        sys.stdout.flush()

        tags = inherit(self.session, self.tag)
        rpm_packages = set()

        for component in self.os.components:
            logging.info("Component {0}".format(component.name))
            success_count = 0
            for tag in tags:
                builds = self.session.query(Build).join(Build.tags).filter(Build.component_id == component.id).filter(Tag.id == tag.id)
                for build in builds:
                    rpm_packages |= set(build.packages)
                if any(builds):
                    success_count += 1

                if success_count == 3:
                    break

        logging.info("Loading package builds from Faf database")

        index = 0
        rpm_packages_count = len(rpm_packages)
        while any(rpm_packages):
            index += 1
            rpm_package = rpm_packages.pop()
            logging.debug("[{0}/{1}] Loading package #{2} {3}".format(index, rpm_packages_count, rpm_package.id, rpm_package.nevra()))
            solvable = self.handle.add_solvable()
            solvable.name = str(rpm_package.name)
            solvable.evr = evr_to_text(rpm_package.build.epoch,
                                       rpm_package.build.version,
                                       rpm_package.build.release)

            solvable.arch = str(rpm_package.arch.name)
            # Store the package id to vendor field.
            solvable.vendor = str(rpm_package.id)
            solvable.add_provides(solv.Dep(pool, pool.rel2id(solvable.nameid, solvable.evrid, solv.REL_EQ, 1)))

            if rpm_package.name.endswith("-devel"):
                static = self.session.query(Package) \
                                     .filter(Package.build_id == rpm_package.build_id) \
                                     .filter(Package.name == rpm_package.name.replace("-devel", "-static")) \
                                     .first()
                if static:
                    solvdep = pool.Dep(static.name.encode("utf-8"))
                    evr = pool.str2id(evr_to_text(static.build.epoch, static.build.version, static.build.release))
                    solvdep = solv.Dep(pool, pool.rel2id(solvdep.id, evr, solv.REL_EQ, 1))
                    solvable.add_requires(solvdep, -solv.SOLVABLE_PREREQMARKER)

            for dep in rpm_package.dependencies:
                # Ignore rpmlib requirements, as they are provided
                # internally by RPM.
                if dep.type == "REQUIRES" and dep.name.startswith("rpmlib("):
                    continue

                # Choose the value of marker
                marker = 0
                if dep.type == "REQUIRES":
                    marker = -solv.SOLVABLE_PREREQMARKER
                elif dep.type == "PROVIDES" and dep.name.startswith("/"):
                    marker = solv.SOLVABLE_FILEMARKER

                # Create a dependency object
                solvdep = pool.Dep(dep.name.encode('utf-8'))
                if dep.epoch is not None or dep.version is not None or dep.release is not None:
                    evr = pool.str2id(evr_to_text(dep.epoch, dep.version, dep.release))
                    flags = rpm_flags_to_solv_flags(dep.flags)
                    solvdep = solv.Dep(pool, pool.rel2id(solvdep.id, evr, flags, 1))

                # Store the dependency object
                if dep.type == "REQUIRES":
                    solvable.add_requires(solvdep, marker)
                elif dep.type == "PROVIDES":
                    solvable.add_provides(solvdep, marker)
                elif dep.type == "OBSOLETES":
                    solvable.add_obsoletes(solvdep)
                elif dep.type == "CONFLICTS":
                    solvable.add_conflicts(solvdep)

        data.internalize()

    def load_if_changed(self):
        logging.info("Checking faf cache repo '{0}'.".format(self.name))
        sys.stdout.flush()

        # Calculate a cookie from metadata contents.
        chksum = solv.Chksum(solv.REPOKEY_TYPE_SHA256)
        count = self.session.query(PackageDependency).count()
        chksum.add(str(count))
        self['cookie'] = chksum.raw()

        if self.use_cached_repo(None, True):
            logging.info("  - using cached metadata")
            return True
        self.pass_data_to_handler()
        if 'incomplete' not in self:
            self.write_cached_repo(None)
        # Must be called after writing the repo.
        self.handle.create_stubs()
        return True

def load_stub(repodata):
    repo = repodata.repo.appdata
    if repo:
        return repo.load_ext(repodata)
    return False

def limit_jobs(pool, jobs, flags, evrstr):
    """
    Take jobs and create new jobs that limit them to certain package
    version.

    pool - data pool
    jobs - the list of jobs to limit
    flags - one of solv.REL_EQ, solv.REL_GT, solv.REL_LT, and solv.REL_ARCH
    evrstr - a string containing either epoch-version-release or architecture

    Returns a list of jobs limiting the version or architecture
    of the provided jobs.
    """
    njobs = []
    evr = pool.str2id(evrstr)
    for j in jobs:
        how = j.how
        sel = how & solv.Job.SOLVER_SELECTMASK
        what = pool.rel2id(j.what, evr, flags)
        if flags == solv.REL_ARCH:
            how |= solv.Job.SOLVER_SETARCH
        elif flags == solv.REL_EQ and sel == solv.Job.SOLVER_SOLVABLE_NAME:
            if evrstr.find('-') >= 0:
                how |= solv.Job.SOLVER_SETEVR
            else:
                how |= solv.Job.SOLVER_SETEV
        njobs.append(pool.Job(how, what))
    return njobs

def dep_glob(pool, name, globname, globdep):
    """
    Create job(s) for certain package name.

    pool - data pool
    name - package name or package name glob to search for
    globname - boolean specifying if package names from repositories
        should also be matched by globbing (simplified regexps)
    globdep - boolean specifying if dependencies (package provides)
        should also be matched by globbing (simplified regexp)

    Returns a list of jobs for the provided package name/glob.  It is
    up to the function caller to specify whether this is a package
    install or removal by setting the 'how' field of the jobs..
    """
    id = pool.str2id(name, False)
    if id:
        match = False
        for s in pool.whatprovides(id):
            if globname and s.nameid == id:
                return [pool.Job(solv.Job.SOLVER_SOLVABLE_NAME, id)]
            match = True
        if match:
            if globname and globdep:
                logging.info("[using capability match for '{0}']".format(name))
            return [pool.Job(solv.Job.SOLVER_SOLVABLE_PROVIDES, id)]
    if not re.search(r'[[*?]', name):
        return []
    if globname:
        # try name glob
        idmatches = {}
        for d in pool.Dataiterator(0, solv.SOLVABLE_NAME, name,
                                   solv.Dataiterator.SEARCH_GLOB):
            s = d.solvable
            if s.installable():
                idmatches[s.nameid] = True
        if idmatches:
            return [pool.Job(solv.Job.SOLVER_SOLVABLE_NAME, id)
                    for id in sorted(idmatches.keys())]
    if globdep:
        # try dependency glob
        idmatches = pool.matchprovidingids(name, solv.Dataiterator.SEARCH_GLOB)
        if idmatches:
            logging.info("[using capability match for '{0}']".format(name))
            return [pool.Job(solv.Job.SOLVER_SOLVABLE_PROVIDES, id)
                    for id in sorted(idmatches)]
    return []

def rpm_flags_to_solv_flags(rpm_flags):
    """
    Convert RPM version comparsion flags (RPMSENSE_*) to libsolv
    version comparison flags.

    See pyfaf/cache/koji_rpm.py for the list of flags.
    """
    solv_flags = 0
    if (rpm_flags & RpmSenseFlags.RPMSENSE_LESS) > 0:
        solv_flags |= solv.REL_LT
    if (rpm_flags & RpmSenseFlags.RPMSENSE_GREATER) > 0:
        solv_flags |= solv.REL_GT
    if (rpm_flags & RpmSenseFlags.RPMSENSE_EQUAL) > 0:
        solv_flags |= solv.REL_EQ
    return solv_flags

def evr_to_text(epoch, version, release):
    """
    Convert epoch, version and release to single string. Epoch and
    release might be None.
    """
    result = ""

    # Hack to be removed when the associated bug is fixed.
    if release == "None":
        release = None
    if epoch == "None":
        epoch = None
    if version == "None":
        version = None

    if epoch is not None:
        result = "{0}:".format(epoch)
    if version is not None:
        result += str(version)
    if release is not None:
        result += "-{0}".format(release)
    return result
