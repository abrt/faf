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

from __future__ import unicode_literals

import sys
if sys.version_info.major == 2:
#Python 2
    import cPickle as pickle
else:
#Python 3+
    import pickle

import os
import shutil
import satyr
from pyfaf.problemtypes import ProblemType
from pyfaf.checker import (Checker,
                           DictChecker,
                           IntChecker,
                           ListChecker,
                           StringChecker)
from pyfaf.common import FafError, log
from pyfaf.queries import (get_archs,
                           get_kernelmodule_by_name,
                           get_package_by_name_build_arch,
                           get_package_by_nevra,
                           get_ssource_by_bpo,
                           get_symbol_by_name_path,
                           get_taint_flag_by_ureport_name)
from pyfaf.retrace import addr2line, demangle, get_function_offset_map
from pyfaf.storage import (KernelModule,
                           KernelTaintFlag,
                           PackageDependency,
                           Report,
                           ReportBacktrace,
                           ReportBtFrame,
                           ReportBtHash,
                           ReportBtKernelModule,
                           ReportBtTaintFlag,
                           ReportBtThread,
                           OpSysComponent,
                           Symbol,
                           SymbolSource,
                           column_len)
from pyfaf.utils.parse import str2bool
from pyfaf.utils.hash import hash_list

__all__ = ["KerneloopsProblem"]


class KerneloopsProblem(ProblemType):
    name = "kerneloops"
    nice_name = "Kernel oops"

    tainted_flags = {
        "module_proprietary": ("P", "Proprietary module has been loaded"),
        "forced_module": ("F", "Module has been forcibly loaded"),
        "smp_unsafe": ("S", "SMP with CPUs not designed for SMP"),
        "forced_removal": ("R", "User forced a module unload"),
        "mce": ("M", "System experienced a machine check exception"),
        "page_release": ("B", "System has hit bad_page"),
        "userspace": ("U", "Userspace-defined naughtiness"),
        "died_recently": ("D", "Kernel has oopsed before"),
        "acpi_overridden": ("A", "ACPI table overridden"),
        "warning": ("W", "Taint on warning"),
        "staging_driver": ("C", "Modules from drivers/staging are loaded"),
        "firmware_workaround": ("I", "Working around severe firmware bug"),
        "module_out_of_tree": ("O", "Out-of-tree module has been loaded"),
        "unsigned_module": ("E", "Unsigned module has been loaded"),
        "soft_lockup": ("L", "A soft lockup previously occurred"),
        "live_patch": ("K", "Kernel has been live patched"),
    }

    checker = DictChecker({
        # no need to check type twice, the toplevel checker already did it
        # "type": StringChecker(allowed=[KerneloopsProblem.name]),
        "component":   StringChecker(pattern=r"^(kernel|xorg-x11-drv-[a-z\-]+)(-[a-zA-Z0-9\-\._]+)?$",
                                     maxlen=column_len(OpSysComponent,
                                                       "name")),

        "version":     StringChecker(pattern=(r"^[0-9]+\.[0-9]+\.[0-9]+"
                                              r"(.[^\-]+)?(\-.*)?$"),
                                     maxlen=column_len(SymbolSource,
                                                       "build_id")),

        "taint_flags": ListChecker(StringChecker(allowed=list(tainted_flags.keys()))),

        "modules":     ListChecker(StringChecker(pattern=r"^[a-zA-Z0-9_]+(\([A-Z\+\-]+\))?$",
                                                 maxlen=column_len(KernelModule,
                                                                   "name")),
                                   mandatory=False),

        "raw_oops": StringChecker(maxlen=Report.__lobs__["oops"],
                                  mandatory=False),

        "frames":      ListChecker(DictChecker({
            "address":         IntChecker(minval=0, maxval=((1 << 64) - 1), mandatory=False),
            "reliable":        Checker(bool),
            "function_name":   StringChecker(pattern=r"^[a-zA-Z0-9_\.]+$",
                                             maxlen=column_len(Symbol,
                                                               "name")),
            "function_offset": IntChecker(minval=0, maxval=((1 << 63) - 1)),
            "function_length": IntChecker(minval=0, maxval=((1 << 63) - 1)),
            "module_name": StringChecker(pattern=r"^[a-zA-Z0-9_]+(\([A-Z\+\-]+\))?$",
                                         mandatory=False),
        }), minlen=1)
    })

    @classmethod
    def install(cls, db, logger=None):
        if logger is None:
            logger = log.getChildLogger(cls.__name__)

        for flag, (char, nice_name) in cls.tainted_flags.items():
            if get_taint_flag_by_ureport_name(db, flag) is None:
                logger.info("Adding kernel taint flag '{0}': {1}"
                            .format(char, nice_name))

                new = KernelTaintFlag()
                new.character = char
                new.ureport_name = flag
                new.nice_name = nice_name
                db.session.add(new)

        db.session.flush()

    @classmethod
    def installed(cls, db):
        for flag in cls.tainted_flags.keys():
            if get_taint_flag_by_ureport_name(db, flag) is None:
                return False

        return True

    def __init__(self, *args, **kwargs):
        super(KerneloopsProblem, self).__init__()

        hashkeys = ["processing.oopshashframes", "processing.hashframes"]
        self.load_config_to_self("hashframes", hashkeys, 16, callback=int)

        cmpkeys = ["processing.oopscmpframes", "processing.cmpframes",
                   "processing.clusterframes"]
        self.load_config_to_self("cmpframes", cmpkeys, 16, callback=int)

        cutkeys = ["processing.oopscutthreshold", "processing.cutthreshold"]
        self.load_config_to_self("cutthreshold", cutkeys, 0.3, callback=float)

        normkeys = ["processing.oopsnormalize", "processing.normalize"]
        self.load_config_to_self("normalize", normkeys, True, callback=str2bool)

        skipkeys = ["retrace.oopsskipsource", "retrace.skipsource"]
        self.load_config_to_self("skipsrc", skipkeys, True, callback=str2bool)

        self.add_lob = {}

        self._kernel_pkg_map = {}
        self.archnames = None

    def _hash_koops(self, koops, taintflags=None, skip_unreliable=False):
        if taintflags is None:
            taintflags = []

        if skip_unreliable:
            frames = [f for f in koops if f["reliable"]]
        else:
            frames = koops

        if len(frames) < 1:
            return None

        hashbase = list(taintflags)
        for frame in frames:
            if not "module_name" in frame:
                module = "vmlinux"
            else:
                module = frame["module_name"]

            if "address" not in frame:
                address = 0
            else:
                address = frame["address"]


            hashbase.append("{0} {1}+{2}/{3} @ {4}"
                            .format(address, frame["function_name"],
                                    frame["function_offset"],
                                    frame["function_length"], module))

        return hash_list(hashbase)

    def _db_backtrace_to_satyr(self, db_backtrace):
        stacktrace = satyr.Kerneloops()

        if len(db_backtrace.threads) < 1:
            self.log_warn("Backtrace #{0} has no usable threads"
                          .format(db_backtrace.id))
            return None

        db_thread = db_backtrace.threads[0]

        if len(db_thread.frames) < 1:
            self.log_warn("Thread #{0} has no usable frames"
                          .format(db_thread.id))
            return None

        for db_frame in db_thread.frames:
            frame = satyr.KerneloopsFrame()
            if db_frame.symbolsource.symbol is not None:
                frame.function_name = db_frame.symbolsource.symbol.name
            else:
                frame.function_name = "??"
            frame.address = db_frame.symbolsource.offset
            frame.function_offset = db_frame.symbolsource.func_offset
            frame.reliable = db_frame.reliable
            if frame.address < 0:
                frame.address += (1 << 64)

            stacktrace.frames.append(frame)

        if self.normalize:
            stacktrace.normalize()

        return stacktrace

    def _db_report_to_satyr(self, db_report):
        if len(db_report.backtraces) < 1:
            self.log_warn("Report #{0} has no usable backtraces"
                          .format(db_report.id))
            return None

        return self._db_backtrace_to_satyr(db_report.backtraces[0])

    def _parse_kernel_build_id(self, build_id, archs):
        """
        Parses the kernel build string such as
        3.10.0-3.fc19.x86_64
        3.10.0-3.fc19.armv7hl.tegra
        2.6.32-358.14.1.el6.i686.PAE
        3.15.6-200.fc20.i686+PAE
        """

        arch = None
        flavour = None

        splitby = "+" if "+" in build_id else "."

        head, tail = build_id.rsplit(splitby, 1)
        if tail in archs:
            arch = tail
        else:
            flavour = tail
            head, tail = head.rsplit(".", 1)
            if not tail in archs:
                raise FafError("Unable to determine architecture from '{0}'"
                               .format(build_id))

            arch = tail

        try:
            version, release = head.rsplit("-", 1)
        except ValueError:
            raise FafError("Unable to determine release from '{0}'"
                           .format(head))

        return version, release, arch, flavour

    def _get_debug_path(self, db, module, db_package):
        """
        Return the path of debuginfo file for
        a given module or None if not found.
        """

        if module == "vmlinux":
            filename = module
        else:
            filename = "{0}.ko.debug".format(module)

        dep = (db.session.query(PackageDependency)
               .filter(PackageDependency.package == db_package)
               .filter(PackageDependency.type == "PROVIDES")
               .filter(PackageDependency.name.like("/%%/{0}"
                                                   .format(filename)))
               .first())

        if dep is None:
            filename = "{0}.ko.debug".format(module.replace("_", "-"))
            dep = (db.session.query(PackageDependency)
                   .filter(PackageDependency.package == db_package)
                   .filter(PackageDependency.type == "PROVIDES")
                   .filter(PackageDependency.name.like("/%%/{0}"
                                                       .format(filename)))
                   .first())


        if dep is None:
            self.log_debug("Unable to find debuginfo for module '{0}'"
                           .format(module))
            return None

        return dep.name

    def validate_ureport(self, ureport):
        # we want to keep unreliable frames without function name RHBZ#1119072
        if "frames" in ureport:
            for frame in ureport["frames"]:
                if ("function_name" not in frame and
                        "reliable" in frame and
                        not frame["reliable"]):
                    frame["function_name"] = "_unknown_"

        KerneloopsProblem.checker.check(ureport)
        return True

    def hash_ureport(self, ureport):
        hashbase = [ureport["component"]]
        hashbase.extend(ureport["taint_flags"])

        for i, frame in enumerate(ureport["frames"]):
            # Instance of 'KerneloopsProblem' has no 'hashframes' member
            # pylint: disable-msg=E1101
            if i >= self.hashframes:
                break

            if not "module_name" in frame:
                module = "vmlinux"
            else:
                module = frame["module_name"]

            hashbase.append("{0} @ {1}".format(frame["function_name"], module))

        return hash_list(hashbase)

    def save_ureport(self, db, db_report, ureport, flush=False, count=1):
        bthash1 = self._hash_koops(ureport["frames"], skip_unreliable=False)
        bthash2 = self._hash_koops(ureport["frames"], skip_unreliable=True)

        if len(db_report.backtraces) < 1:
            db_backtrace = ReportBacktrace()
            db_backtrace.report = db_report
            db.session.add(db_backtrace)

            db_thread = ReportBtThread()
            db_thread.backtrace = db_backtrace
            db_thread.crashthread = True
            db.session.add(db_thread)

            db_bthash1 = ReportBtHash()
            db_bthash1.backtrace = db_backtrace
            db_bthash1.hash = bthash1
            db_bthash1.type = "NAMES"
            db.session.add(db_bthash1)

            if bthash2 is not None and bthash1 != bthash2:
                db_bthash2 = ReportBtHash()
                db_bthash2.backtrace = db_backtrace
                db_bthash2.hash = bthash2
                db_bthash2.type = "NAMES"
                db.session.add(db_bthash2)

            new_symbols = {}
            new_symbolsources = {}

            i = 0
            for frame in ureport["frames"]:
                # OK, this is totally ugly.
                # Frames may contain inlined functions, that would normally
                # require shifting all frames by 1 and inserting a new one.
                # There is no way to do this efficiently with SQL Alchemy
                # (you need to go one by one and flush after each) so
                # creating a space for additional frames is a huge speed
                # optimization.
                i += 10

                # nah, another hack, deals with wrong parsing
                if frame["function_name"].startswith("0x"):
                    continue

                if not "module_name" in frame:
                    module = "vmlinux"
                else:
                    module = frame["module_name"]

                db_symbol = get_symbol_by_name_path(db, frame["function_name"],
                                                    module)
                if db_symbol is None:
                    key = (frame["function_name"], module)
                    if key in new_symbols:
                        db_symbol = new_symbols[key]
                    else:
                        db_symbol = Symbol()
                        db_symbol.name = frame["function_name"]
                        db_symbol.normalized_path = module
                        db.session.add(db_symbol)
                        new_symbols[key] = db_symbol

                # this doesn't work well. on 64bit, kernel maps to
                # the end of address space (64bit unsigned), but in
                # postgres bigint is 64bit signed and can't save
                # the value - let's just map it to signed
                if "address" in frame:
                    if frame["address"] >= (1 << 63):
                        address = frame["address"] - (1 << 64)
                    else:
                        address = frame["address"]
                else:
                    address = 0

                db_symbolsource = get_ssource_by_bpo(db, ureport["version"],
                                                     module, address)
                if db_symbolsource is None:
                    key = (ureport["version"], module, address)
                    if key in new_symbolsources:
                        db_symbolsource = new_symbolsources[key]
                    else:
                        db_symbolsource = SymbolSource()
                        db_symbolsource.path = module
                        db_symbolsource.offset = address
                        db_symbolsource.func_offset = frame["function_offset"]
                        db_symbolsource.symbol = db_symbol
                        db_symbolsource.build_id = ureport["version"]
                        db.session.add(db_symbolsource)
                        new_symbolsources[key] = db_symbolsource

                db_frame = ReportBtFrame()
                db_frame.thread = db_thread
                db_frame.order = i
                db_frame.symbolsource = db_symbolsource
                db_frame.inlined = False
                db_frame.reliable = frame["reliable"]
                db.session.add(db_frame)

            for taintflag in ureport["taint_flags"]:
                db_taintflag = get_taint_flag_by_ureport_name(db, taintflag)
                if db_taintflag is None:
                    self.log_warn("Skipping unsupported taint flag '{0}'"
                                  .format(taintflag))
                    continue

                db_bttaintflag = ReportBtTaintFlag()
                db_bttaintflag.backtrace = db_backtrace
                db_bttaintflag.taintflag = db_taintflag
                db.session.add(db_bttaintflag)

            if "modules" in ureport:
                new_modules = {}

                # use set() to remove duplicates
                for module in set(ureport["modules"]):
                    idx = module.find("(")
                    if idx >= 0:
                        module = module[:idx]

                    db_module = get_kernelmodule_by_name(db, module)
                    if db_module is None:
                        if module in new_modules:
                            db_module = new_modules[module]
                        else:
                            db_module = KernelModule()
                            db_module.name = module
                            db.session.add(db_module)
                            new_modules[module] = db_module

                    db_btmodule = ReportBtKernelModule()
                    db_btmodule.kernelmodule = db_module
                    db_btmodule.backtrace = db_backtrace
                    db.session.add(db_btmodule)

            # do not overwrite an existing oops
            if not db_report.has_lob("oops"):
                # do not append here, but create a new dict
                # we only want save_ureport_post_flush process the most
                # recently saved report
                self.add_lob = {db_report: ureport["raw_oops"].encode("utf-8")}

        if flush:
            db.session.flush()

    def save_ureport_post_flush(self):
        for report, raw_oops in self.add_lob.items():
            report.save_lob("oops", raw_oops)

        # clear the list so that re-calling does not make problems
        self.add_lob = {}

    def get_component_name(self, ureport):
        return ureport["component"]


    def compare(self, db_report1, db_report2):
        satyr_report1 = self._db_report_to_satyr(db_report1)
        satyr_report2 = self._db_report_to_satyr(db_report2)
        return satyr_report1.distance(satyr_report2)

    def compare_many(self, db_reports):
        self.log_info("Loading reports")

        reports = []
        ret_db_reports = []

        i = 0
        for db_report in db_reports:
            i += 1

            self.log_debug("[{0} / {1}] Loading report #{2}"
                           .format(i, len(db_reports), db_report.id))
            report = self._db_report_to_satyr(db_report)

            if report is None:
                self.log_debug("Unable to build satyr.Kerneloops")
                continue

            reports.append(report)
            ret_db_reports.append(db_report)

        self.log_info("Calculating distances")
        distances = satyr.Distances(reports, len(reports))

        return ret_db_reports, distances

    def _get_ssources_for_retrace_query(self, db):
        koops_syms = (db.session.query(SymbolSource.id)
                      .join(ReportBtFrame)
                      .join(ReportBtThread)
                      .join(ReportBacktrace)
                      .join(Report)
                      .filter(Report.type == KerneloopsProblem.name)
                      .subquery())

        q = (db.session.query(SymbolSource)
             .filter(SymbolSource.id.in_(koops_syms))
             .filter((SymbolSource.source_path == None) |
                     (SymbolSource.line_number == None))
             .filter(SymbolSource.symbol_id != None))
        return q

    def find_packages_for_ssource(self, db, db_ssource):
        if db_ssource.build_id is None:
            self.log_debug("No kernel information for '{0}' @ '{1}'"
                           .format(db_ssource.symbol.name, db_ssource.path))
            return db_ssource, (None, None, None)

        if db_ssource.build_id in self._kernel_pkg_map:
            return db_ssource, self._kernel_pkg_map[db_ssource.build_id]

        if self.archnames is None:
            self.archnames = set(arch.name for arch in get_archs(db))

        kernelver = self._parse_kernel_build_id(db_ssource.build_id, self.archnames)
        version, release, arch, flavour = kernelver

        if flavour is not None:
            basename = "kernel-{0}-debuginfo".format(flavour)
        else:
            basename = "kernel-debuginfo"

        db_debug_pkg = get_package_by_nevra(db, basename, 0,
                                            version, release, arch)

        nvra = "{0}-{1}-{2}.{3}".format(basename, version, release, arch)

        db_src_pkg = None
        if db_debug_pkg is None:
            self.log_debug("Package {0} not found in storage".format(nvra))
        elif not self.skipsrc:
            srcname = "kernel-debuginfo-common-{0}".format(arch)
            db_src_pkg = get_package_by_name_build_arch(db, srcname,
                                                        db_debug_pkg.build,
                                                        db_debug_pkg.arch)

            if db_src_pkg is None:
                self.log_debug("Package {0}-{1}-{2}.{3} not found in storage"
                               .format(srcname, version, release, arch))

        result = db_debug_pkg, db_debug_pkg, db_src_pkg
        self._kernel_pkg_map[db_ssource.build_id] = result

        return db_ssource, result

    def retrace(self, db, task):
        new_symbols = {}
        new_symbolsources = {}

        debug_paths = set(os.path.join(task.debuginfo.unpacked_path, fname[1:])
                          for fname in task.debuginfo.debug_files)
        if task.debuginfo.debug_files is not None:
            db_debug_pkg = task.debuginfo.db_package
            if db_debug_pkg.has_lob("offset_map"):
                with db_debug_pkg.get_lob_fd("offset_map") as fd:
                    offset_map = pickle.load(fd)
            else:
                offset_map = get_function_offset_map(debug_paths)
                db_debug_pkg.save_lob("offset_map", pickle.dumps(offset_map))
        else:
            offset_map = {}

        for bin_pkg, db_ssources in task.binary_packages.items():
            i = 0
            for db_ssource in db_ssources:
                i += 1
                module = db_ssource.path
                self.log_info(u"[{0} / {1}] Processing '{2}' @ '{3}'"
                              .format(i, len(db_ssources),
                                      db_ssource.symbol.name, module))

                if db_ssource.path == "vmlinux":
                    address = db_ssource.offset
                    if address < 0:
                        address += (1 << 64)
                else:
                    if module not in offset_map:
                        self.log_debug("Module '{0}' not found in package '{1}'"
                                       .format(module, task.debuginfo.nvra))
                        db_ssource.retrace_fail_count += 1
                        continue

                    module_map = offset_map[module]

                    symbol_name = db_ssource.symbol.name
                    if symbol_name not in module_map:
                        symbol_name = symbol_name.lstrip("_")

                    if symbol_name not in module_map:
                        self.log_debug("Function '{0}' not found in module "
                                       "'{1}'".format(db_ssource.symbol.name,
                                                      module))
                        db_ssource.retrace_fail_count += 1
                        continue

                    address = module_map[symbol_name] + db_ssource.func_offset

                debug_dir = os.path.join(task.debuginfo.unpacked_path,
                                         "usr", "lib", "debug")
                debug_path = self._get_debug_path(db, module,
                                                  task.debuginfo.db_package)
                if debug_path is None:
                    db_ssource.retrace_fail_count += 1
                    continue

                try:
                    abspath = os.path.join(task.debuginfo.unpacked_path,
                                           debug_path[1:])
                    results = addr2line(abspath, address, debug_dir)
                    results.reverse()
                except FafError as ex:
                    self.log_debug("addr2line failed: {0}".format(str(ex)))
                    db_ssource.retrace_fail_count += 1
                    continue

                inl_id = 0
                while len(results) > 1:
                    inl_id += 1

                    funcname, srcfile, srcline = results.pop()
                    self.log_debug("Unwinding inlined function '{0}'"
                                   .format(funcname))
                    # hack - we have no offset for inlined symbols
                    # let's use minus source line to avoid collisions
                    offset = -srcline

                    db_ssource_inl = get_ssource_by_bpo(db, db_ssource.build_id,
                                                        db_ssource.path, offset)
                    if db_ssource_inl is None:
                        key = (db_ssource.build_id, db_ssource.path, offset)
                        if key in new_symbolsources:
                            db_ssource_inl = new_symbolsources[key]
                        else:
                            db_symbol_inl = get_symbol_by_name_path(db,
                                                                    funcname,
                                                                    module)

                            if db_symbol_inl is None:
                                sym_key = (funcname, module)
                                if sym_key in new_symbols:
                                    db_symbol_inl = new_symbols[sym_key]
                                else:
                                    db_symbol_inl = Symbol()
                                    db_symbol_inl.name = funcname
                                    db_symbol_inl.normalized_path = module
                                    db.session.add(db_symbol_inl)
                                    new_symbols[sym_key] = db_symbol_inl

                            db_ssource_inl = SymbolSource()
                            db_ssource_inl.symbol = db_symbol_inl
                            db_ssource_inl.build_id = db_ssource.build_id
                            db_ssource_inl.path = module
                            db_ssource_inl.offset = offset
                            db_ssource_inl.source_path = srcfile
                            db_ssource_inl.line_number = srcline
                            db.session.add(db_ssource_inl)
                            new_symbolsources[key] = db_ssource_inl

                    for db_frame in db_ssource.frames:
                        db_frames = sorted(db_frame.thread.frames,
                                           key=lambda f: f.order)
                        idx = db_frames.index(db_frame)
                        if idx > 0:
                            prevframe = db_frame.thread.frames[idx - 1]
                            if (prevframe.inlined and
                                    prevframe.symbolsource == db_ssource_inl):
                                continue

                        db_newframe = ReportBtFrame()
                        db_newframe.symbolsource = db_ssource_inl
                        db_newframe.thread = db_frame.thread
                        db_newframe.inlined = True
                        db_newframe.order = db_frame.order - inl_id
                        db.session.add(db_newframe)

                funcname, srcfile, srcline = results.pop()
                self.log_debug("Result: {0}".format(funcname))
                db_symbol = get_symbol_by_name_path(db, funcname, module)
                if db_symbol is None:
                    key = (funcname, module)
                    if key in new_symbols:
                        db_symbol = new_symbols[key]
                    else:
                        self.log_debug("Creating new symbol '{0}' @ '{1}'"
                                       .format(funcname, module))
                        db_symbol = Symbol()
                        db_symbol.name = funcname
                        db_symbol.normalized_path = module
                        db.session.add(db_symbol)

                        new_symbols[key] = db_symbol

                if db_symbol.nice_name is None:
                    db_symbol.nice_name = demangle(funcname)

                db_ssource.symbol = db_symbol
                db_ssource.source_path = srcfile
                db_ssource.line_number = srcline

        if task.debuginfo is not None:
            self.log_debug("Removing {0}".format(task.debuginfo.unpacked_path))
            shutil.rmtree(task.debuginfo.unpacked_path, ignore_errors=True)

        if task.source is not None and task.source.unpacked_path is not None:
            self.log_debug("Removing {0}".format(task.source.unpacked_path))
            shutil.rmtree(task.source.unpacked_path, ignore_errors=True)

    def check_btpath_match(self, ureport, parser):
        for frame in ureport["frames"]:
            # vmlinux
            if not "module_name" in frame:
                continue

            match = parser.match(frame["module_name"])

            if match is not None:
                return True

        return False

    def find_crash_function(self, db_backtrace):
        satyr_koops = self._db_backtrace_to_satyr(db_backtrace)
        return satyr_koops.frames[0].function_name
