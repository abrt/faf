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
from typing import Optional
from urllib.request import urlopen

from sqlalchemy.orm.query import Query

from pyfaf.actions import Action
from pyfaf.queries import get_external_faf_by_id
from pyfaf.storage import Report, ReportExternalFaf


class ExternalFafLink(Action):
    name = "extfaflink"


    def _get_reports_query(self, db) -> Query:
        return db.session.query(Report)

    def _has_external_report(self, db_report, external_id) -> bool:
        for db_external_report in db_report.external_faf_reports:
            if external_id == db_external_report.external_id:
                return True

        return False

    def _find_hash(self, hashvalue, baseurl, parser) -> Optional[int]:
        url = "{0}/reports/bthash/{1}".format(baseurl, hashvalue)

        try:
            urlfile = urlopen(url)  # pylint: disable=consider-using-with
            urlfile.close()
        except: # pylint: disable=bare-except
            self.log_warn("Could not find external report id for hash {0}"
                          .format(hashvalue))
            return None

        if urlfile.code != 200:
            return None

        match = parser.match(urlfile.geturl())
        if match is None:
            return None

        return int(match.group(1))

    def run(self, cmdline, db) -> int:
        db_external_faf = get_external_faf_by_id(db, cmdline.INSTANCE_ID)
        if db_external_faf is None:
            self.log_error("An external FAF instance with ID #{0} does not "
                           "exist".format(cmdline.INSTANCE_ID))
            return 1

        parser = re.compile(r"{0}/reports/([0-9]+)/"
                            .format(db_external_faf.baseurl))

        db_reports = self._get_reports_query(db)
        cnt = db_reports.count()

        for i, db_report in enumerate(db_reports, start=1):

            hashes = set()
            self.log_info("[{0} / {1}] Processing report #{2}"
                          .format(i, cnt, db_report.id))

            for db_reporthash in db_report.hashes:
                self.log_debug("Adding report hash '%s'", db_reporthash.hash)
                hashes.add(db_reporthash.hash)

            for db_backtrace in db_report.backtraces:
                for db_bthash in db_backtrace.hashes:
                    self.log_debug("Adding backtrace hash '%s'", db_bthash.hash)
                    hashes.add(db_bthash.hash)

            hashes_len = len(hashes)
            for j, hashvalue in enumerate(hashes, start=1):

                self.log_debug("[%d / %d] Processing hash '%s'", j, hashes_len, hashvalue)
                external_id = self._find_hash(hashvalue,
                                              db_external_faf.baseurl,
                                              parser)
                if external_id is None:
                    continue

                if self._has_external_report(db_report, external_id):
                    self.log_debug("Skipping existing external report #%d", external_id)
                    continue

                self.log_info("Adding external report #{0}"
                              .format(external_id))

                db_externalfaf = ReportExternalFaf()
                db_externalfaf.report = db_report
                db_externalfaf.faf_instance = db_external_faf
                db_externalfaf.external_id = external_id
                db.session.add(db_externalfaf)

        db.session.flush()
        return 0

    def tweak_cmdline_parser(self, parser) -> None:
        parser.add_ext_instance(helpstr="ID of the external FAF instance to link against")
