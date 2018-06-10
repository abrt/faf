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

from pyfaf.actions import Action
from pyfaf.queries import get_external_faf_by_id


class ExternalFafDelete(Action):
    name = "extfafdel"


    def run(self, cmdline, db):
        for instance_id in cmdline.INSTANCE_ID:
            db_instance = get_external_faf_by_id(db, instance_id)
            if db_instance is None:
                self.log_warn("The instance with ID {0} is not defined "
                              "in storage".format(instance_id))
                continue

            self.log_debug("Processing instance '{0}'".format(db_instance.name))

            if db_instance.reports:
                if not cmdline.cascade:
                    self.log_warn("The instance '{0}' with ID {1} has reports "
                                  "but --cascade has not been specified"
                                  .format(db_instance.name, instance_id))
                    continue

                for db_external_report in db_instance.reports:
                    self.log_debug("Deleting assigned report #{0}"
                                   .format(db_external_report.external_id))
                    db.session.delete(db_external_report)

            db.session.delete(db_instance)
            self.log_info("Deleted the instance '{0}' with ID {1}"
                          .format(db_instance.name, instance_id))

        db.session.flush()

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("INSTANCE_ID", action="append", type=int,
                            default=[], help="FAF instance ID to delete")
        parser.add_argument("--cascade", action="store_true", default=False,
                            help="Delete reports assigned to the instance")
