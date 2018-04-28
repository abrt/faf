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

import datetime
import re
import urllib
from pyfaf.actions import Action
from pyfaf.bugtrackers import bugtrackers
from pyfaf.bugtrackers.bugzilla import Bugzilla
from pyfaf.storage import OpSysComponent, ReportExternalFaf


class ExternalFafCloneBZ(Action):
    name = "extfafclonebz"

    BZ_PARSER = re.compile("BZ#([0-9]+)")

    def __init__(self):
        super(ExternalFafCloneBZ, self).__init__()

        self.load_config_to_self("baseurl", ["clonebz.baseurl"], None)

    def _get_bugs(self, url, bz):
        result = set()

        self.log_debug("Opening URL {0}".format(url))
        url = urllib.urlopen(url)
        code = url.getcode()
        if code != 200:
            self.log_debug("Unexpected HTTP code: {0}".format(code))
            return []

        body = url.read()
        match = self.BZ_PARSER.search(body)
        while True:
            match = self.BZ_PARSER.search(body)
            if match is None:
                break

            bug_id = int(match.group(1))
            body = body.replace(match.group(0), "")
            try:
                bug = bz.bz.getbug(bug_id)
                while (bug.status == "CLOSED" and
                       bug.resolution == "DUPLICATE"):
                    self.log_debug("Bug {0} is a duplicate of {1}"
                                   .format(bug.id, bug.dupe_of))
                    bug = bz.bz.getbug(bug.dupe_of)
            except Exception as ex:
                self.log_debug("Unable to fetch bug: {0}".format(str(ex)))
                continue

            result.add(bug)

        return result

    def _nvra(self, db_unknown_package):
        return ("{0}-{1}-{2}.{3}".format(db_unknown_package.name,
                                         db_unknown_package.version,
                                         db_unknown_package.release,
                                         db_unknown_package.arch))

    def run(self, cmdline, db):
        self.log_warn("This is an experimental script and is not guaranteed "
                      "to give any meaningful results. As a side-effect it may "
                      "create a large number of bugs in the selected Bugzilla "
                      "instance so be sure you really know what you are doing.")

        if cmdline.baseurl is not None:
            self.baseurl = cmdline.baseurl

        bz = bugtrackers[cmdline.bugtracker]
        if not isinstance(bz, Bugzilla):
            self.log_error("The selected bug tracker must be Bugzilla instance")
            return 1

        bz._connect()

        db_comps = db.session.query(OpSysComponent)
        skip_components = [c.name for c in db_comps if len(c.releases) == 0]

        db_external_reports = db.session.query(ReportExternalFaf).all()

        i = 0
        for db_external_report in db_external_reports:
            i += 1

            db_instance = db_external_report.faf_instance

            self.log_info("[{0} / {1}] Processing {2} report #{3}"
                          .format(i, len(db_external_reports),
                                  db_instance.name,
                                  db_external_report.external_id))

            if len(db_external_report.report.bz_bugs) > 0:
                self.log_debug("Report #{0} has already a BZ assigned"
                               .format(db_external_report.report_id))
                continue

            now = datetime.datetime.utcnow()
            two_weeks = datetime.timedelta(days=140)
            if now - db_external_report.report.last_occurrence >= two_weeks:
                self.log_debug("Report #{0} is older than 14 days, skipping"
                               .format(db_external_report.report_id))
                continue

            url = "{0}/reports/{1}".format(db_instance.baseurl,
                                           db_external_report.external_id)
            bugs = self._get_bugs(url, bz)
            if len(bugs) < 1:
                self.log_debug("No bugs found")
                continue

            for bug in bugs:
                self.log_debug("Processing bug #{0}".format(bug.id))

                if bug.component in skip_components:
                    self.log_debug("Bug #{0} is reported against "
                                   "an unsupported component {1}"
                                   .format(bug.id, bug.component))
                    continue

                if bug.status == "CLOSED":
                    status = "CLOSED %s" % bug.resolution
                else:
                    status = bug.status

                if cmdline.dry_run:
                    self.log_warn("Dry-run enabled, not touching BZ")
                    continue

                self.log_info("Cloning BZ #{0} ({1})".format(bug.id, status))
                reporturl = "{0}/{1}".format(self.baseurl.rstrip("/"),
                                             db_external_report.report_id)
                newbug = bz.clone_bug(bug.id, cmdline.NEW_PRODUCT,
                                      cmdline.NEW_VERSION, url=reporturl)
                self.log_info("Created bug #{0}".format(newbug.id))

                db_packages = db_external_report.report.unknown_packages
                package_list = "\n".join(self._nvra(p) for p in db_packages
                                         if p.type.lower() == "crashed")

                comment = ("The same problem has been detected in {0}. "
                           "The following packages are affected:\n\n{1}"
                           .format(cmdline.NEW_PRODUCT, package_list))
                newbug.addcomment(comment)
                db_bzbug = bz.download_bug_to_storage(db, newbug.id)

                db_reportbz = ReportBz()
                db_reportbz.report = db_external_report.report
                db_reportbz.bzbug = db_bzbug
                db.session.add(db_reportbz)
                db.session.flush()

    def tweak_cmdline_parser(self, parser):
        parser.add_bugtracker()
        parser.add_argument("NEW_PRODUCT", help="Product to clone bugs against")
        parser.add_argument("NEW_VERSION", help="Version of the product")
        parser.add_argument("--baseurl",
                            help="Prefix for referrencing local bugs")
