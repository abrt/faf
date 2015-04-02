# Copyright (C) 2015  ABRT Team
# Copyright (C) 2015  Red Hat, Inc.
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

from pyfaf.actions import Action
from pyfaf.bugtrackers import bugtrackers
from pyfaf.queries import (get_mantis_bug,
                           get_report_by_hash,
                           get_reportmantis,
                           get_osrelease,
                           get_bugtracker_by_name)
from pyfaf.storage import ReportMantis


class AttachCentosBugs(Action):
    """
    Looks up all bugs created using ABRT on CentOS MantisBT and attaches them
    to reports using the bthash from URL. This is a workaround until proper
    attaching is supported by the ABRT client.
    """
    name = "attach-centos-bugs"

    def run(self, cmdline, db):
        mbt = bugtrackers["centos-mantisbt"]
        db_tracker = get_bugtracker_by_name(db, "centos-mantisbt")
        for bug_id in mbt.list_bugs():
            self.log_info("Processing Mantis issue #{0}".format(bug_id))
            bug = mbt.mc.mc_issue_get(mbt.user, mbt.password, bug_id)
            bug_dict = mbt._preprocess_bug(bug)
            if bug_dict and bug_dict.get("url", False):
                url = bug_dict["url"]
                report_hash = url.split("/")[-1]
                db_report = get_report_by_hash(db, report_hash)
                if db_report is None:
                    self.log_info("Report with hash {0} not found."
                                  .format(report_hash))
                    continue
                db_mantisbug = get_mantis_bug(db, bug_id, db_tracker.id)
                if db_mantisbug is None:
                    self.log_info("Downloading bug to storage...")
                    db_mantisbug = mbt.download_bug_to_storage(db, bug_id)
                    if db_mantisbug is None:
                        self.log_info("Failed to download bug.")
                        continue

                db_rm = (db.session.query(ReportMantis)
                                   .filter(ReportMantis.report == db_report)
                                   .filter(ReportMantis.mantisbug == db_mantisbug)
                                   .first())
                if db_rm is None:
                    db_rm = ReportMantis()
                    db_rm.mantisbug = db_mantisbug
                    db_rm.report = db_report
                    db.session.add(db_rm)
                    db.session.flush()
                    self.log_info("Associated issue #{0} with report #{1}."
                                  .format(bug_id, db_report.id))
            else:
                self.log_info("Not a valid ABRT issue.".format(bug_id))
