# Copyright (C) 2017  ABRT Team
# Copyright (C) 2017  Red Hat, Inc.
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

from pyfaf.actions import Action
from pyfaf.storage.debug import InvalidUReport

class DeleteInvalidUReports(Action):
    name = "delete-invalid-ureports"

    def run(self, cmdline, db):
        if cmdline.age:
            age = int(cmdline.age)
            if age < 0:
                self.log_error("Negative age given: {0}, exiting".format(age))
                return 1

            current_time = datetime.datetime.utcnow()
            given_days_ago = current_time - datetime.timedelta(days=age)

            query = (db.session.query(InvalidUReport)
                    .filter(InvalidUReport.date < given_days_ago))
        else:
            self.log_info("No age given, selecting all invalid ureports")
            query = db.session.query(InvalidUReport)

        self.log_info("{0} invalid ureports will be removed"
                        .format(query.count()))

        if cmdline.dry_run:
            self.log_info("Dry run active, removal will be skipped")
        else:
            # delete ureport from disk
            for inv_ureport in query.all():
                if inv_ureport.has_lob("ureport"):
                    inv_ureport.del_lob("ureport")
            # delete ureports from database
            query.delete()

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("--age", default=None,
                            help="delete older than AGE days")
