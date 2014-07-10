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

import re
import urllib
from pyfaf.actions import Action
from pyfaf.queries import get_external_faf_by_id
from pyfaf.storage import Report, ReportExternalFaf


class ExternalFafLink(Action):
    name = "extfaflink"

    def __init__(self):
        super(ExternalFafLink, self).__init__()

    def _get_reports_query(self, db):
        return db.session.query(Report)

    def _has_external_report(self, db_report, external_id):
        for db_external_report in db_report.external_faf_reports:
            if external_id == db_external_report.external_id:
                return True

        return False

    def _find_hash(self, hashvalue, baseurl, parser):
        url = "{0}/reports/bthash/{1}".format(baseurl, hashvalue)

        try:
            urlfile = urllib.urlopen(url)
            urlfile.close()
        except:
            return None

        if urlfile.code != 200:
            return None

        match = parser.match(urlfile.geturl())
        if match is None:
            return None

        return int(match.group(1))

    def run(self, cmdline, db):
        db_external_faf = get_external_faf_by_id(db, cmdline.INSTANCE_ID)
        if db_external_faf is None:
            self.log_error("An external FAF instance with ID #{0} does not "
                           "exist".format(cmdline.INSTANCE_ID))
            return 1

        parser = re.compile(r"{0}/reports/([0-9]+)/"
                            .format(db_external_faf.baseurl))

        db_reports = self._get_reports_query(db)
        cnt = db_reports.count()

        i = 0
        for db_report in db_reports:
            i += 1

            hashes = set()
            self.log_info("[{0} / {1}] Processing report #{2}"
                          .format(i, cnt, db_report.id))

            for db_reporthash in db_report.hashes:
                self.log_debug("Adding report hash '{0}'"
                               .format(db_reporthash.hash))
                hashes.add(db_reporthash.hash)

            for db_backtrace in db_report.backtraces:
                for db_bthash in db_backtrace.hashes:
                    self.log_debug("Adding backtrace hash '{0}'"
                                   .format(db_bthash.hash))
                    hashes.add(db_bthash.hash)

            j = 0
            for hashvalue in hashes:
                j += 1

                self.log_debug("[{0} / {1}] Processing hash '{2}'"
                               .format(j, len(hashes), hashvalue))
                external_id = self._find_hash(hashvalue,
                                              db_external_faf.baseurl,
                                              parser)
                if external_id is None:
                    continue

                if self._has_external_report(db_report, external_id):
                    self.log_debug("Skipping existing external report #{0}"
                                   .format(external_id))
                    continue

                self.log_info("Adding external report #{0}"
                              .format(external_id))

                db_externalfaf = ReportExternalFaf()
                db_externalfaf.report = db_report
                db_externalfaf.faf_instance = db_external_faf
                db_externalfaf.external_id = external_id
                db.session.add(db_externalfaf)

        db.session.flush()

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("INSTANCE_ID", type=int,
                            help=("ID of the external FAF "
                                  "instance to link against"))
