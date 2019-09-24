# Copyright (C) 2014  ABRT Team
# Copyright (C) 2014  Red Hat, Inc.
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

import hashlib

from pyfaf.actions import Action
from pyfaf.common import FafError
from pyfaf.problemtypes import problemtypes
from pyfaf.queries import get_reports_by_type, get_report
from pyfaf.storage import ReportHash


class AddCompatHashes(Action):
    name = "addcompathashes"


    def _unmap_offset(self, offset):
        if offset < 0:
            offset += 1 << 63

        return offset

    def _hash_backtrace(self, db_backtrace, hashbase=None, offset=False):
        if hashbase is None:
            hashbase = []

        crashthreads = [t for t in db_backtrace.threads if t.crashthread]
        if not crashthreads:
            raise FafError("No crash thread found")

        if len(crashthreads) > 1:
            raise FafError("Multiple crash threads found")

        frames = [f for f in crashthreads[0].frames if not f.inlined][:16]

        hasnames = all([f.symbolsource.symbol is not None and
                        f.symbolsource.symbol.name is not None and
                        f.symbolsource.symbol.name != "??" for f in frames])
        hashashes = all([f.symbolsource.hash is not None for f in frames])

        # use function names if available
        if hasnames:
            # also hash offset for reports that use it as line numbers
            # these reports always have function names
            if offset:
                hashbase.extend(["{0} @ {1} + {2}"
                                 .format(f.symbolsource.symbol.name,
                                         f.symbolsource.path,
                                         f.symbolsource.offset) for f in frames])
            else:
                hashbase.extend(["{0} @ {1}"
                                 .format(f.symbolsource.symbol.name,
                                         f.symbolsource.path) for f in frames])
        # fallback to hashes
        elif hashashes:
            hashbase.extend(["{0} @ {1}"
                             .format(f.symbolsource.hash,
                                     f.symbolsource.path) for f in frames])
        else:
            raise FafError("either function names or hashes are required")

        return hashlib.sha1("\n".join(hashbase).encode("utf-8")).hexdigest()

    def run(self, cmdline, db):
        if cmdline.problemtype is None or not cmdline.problemtype:
            ptypes = list(problemtypes.keys())
        else:
            ptypes = []
            for ptype in cmdline.problemtype:
                if ptype not in problemtypes:
                    self.log_warn("Problem type '{0}' is not supported"
                                  .format(ptype))
                    continue

                ptypes.append(ptype)

        if not ptypes:
            self.log_info("Nothing to do")
            return 0

        for i, ptype in enumerate(ptypes, start=1):
            problemtype = problemtypes[ptype]

            self.log_info("[{0} / {1}] Processing problem type '{2}'"
                          .format(i, len(ptypes), problemtype.nice_name))
            db_reports = get_reports_by_type(db, ptype)

            for j, db_report in enumerate(db_reports, start=1):

                self.log_info("  [{0} / {1}] Processing report #{2}"
                              .format(j, len(db_reports), db_report.id))

                hashes = set()
                for k, db_backtrace in enumerate(db_report.backtraces, start=1):

                    self.log_debug("\t[%d / %d] Processing backtrace #%d",
                                   k, len(db_report.backtraces), db_backtrace.id)
                    try:
                        component = db_report.component.name
                        include_offset = ptype.lower() == "python"
                        bthash = self._hash_backtrace(db_backtrace,
                                                      hashbase=[component],
                                                      offset=include_offset)
                        self.log_debug("\t%s", bthash)
                        db_dup = get_report(db, bthash)
                        if db_dup is None:
                            self.log_info("    Adding hash '{0}'"
                                          .format(bthash))
                            if not bthash in hashes:
                                db_reporthash = ReportHash()
                                db_reporthash.report = db_report
                                db_reporthash.hash = bthash
                                db.session.add(db_reporthash)
                                hashes.add(bthash)
                        elif db_dup == db_report:
                            self.log_debug("\tHash '%s' already assigned", bthash)
                        else:
                            self.log_warn(("    Conflict! Skipping hash '{0}'"
                                           " (report #{1})").format(bthash,
                                                                    db_dup.id))
                    except FafError as ex:
                        self.log_warn("    {0}".format(str(ex)))
                        continue

                db.session.flush()
        return 0

    def tweak_cmdline_parser(self, parser):
        parser.add_problemtype(multiple=True)
