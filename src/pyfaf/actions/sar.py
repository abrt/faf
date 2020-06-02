# Copyright (C) 2018  ABRT Team
# Copyright (C) 2018  Red Hat, Inc.
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

import os
from pyfaf.actions import Action
from pyfaf.storage.user import User
from pyfaf.utils.user import UserDataDumper

class SubjectAccessRequest(Action):
    name = "sar"

    def run(self, cmdline, db) -> int:
        mail = os.environ.get("SAR_EMAIL", None)
        username = os.environ.get("SAR_USERNAME", None)

        if not mail and not username:
            print("Environment variables SAR_USERNAME, SAR_EMAIL were not set.")
            return 1

        if mail:
            dumper = UserDataDumper(db, mail)
            print(dumper.dump(pretty=True))
            return 0

        if username:
            usermail = db.session.query(User).filter(User.username == username).first()
            if usermail is not None:
                dumper = UserDataDumper(db, usermail.mail)
                print(dumper.dump(pretty=True))
            else:
                print("User '{0}' was not found.".format(username))

        return 0
