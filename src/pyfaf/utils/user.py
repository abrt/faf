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
try:
    import simplejson as json
except ImportError:
    import json

from pyfaf import queries
from pyfaf.utils.web import server_url

def get_url(page_type, number):
    """
    Return absolute URL if the server_name was configured otherwise
    just return the provided number.
    """
    url = server_url()
    if url:
        return os.path.join(url, page_type, str(number))

    return str(number)


class UserDataDumper(object):
    def __init__(self, db, mail):
        self.mail = mail
        self.db = db

    def dump(self, pretty=False):
        if pretty:
            return json.dumps(self.data, indent=2)
        return json.dumps(self.data)

    @property
    def data(self):
        data = self.user_info
        if data:
            data["Reassigned Problems"] = self.problems
            data["Archived Reports"] = self.reports
        else:
            data = dict()

        data["Bugzilla"] = self.bugzillas
        data["Contact Mail Reports"] = self.contact_mails

        return data

    @property
    def user_info(self):
        fas_user = queries.get_user_by_mail(self.db, self.mail).first()
        if fas_user:
            return {'Username': fas_user.username, 'Mail': fas_user.mail}
        return {}

    @property
    def bugzillas(self):
        bz_user = queries.get_bz_user(self.db, self.mail)
        if not bz_user:
            return {}

        user_bugzillas = queries.get_bugzillas_by_uid(self.db, bz_user.id)
        bz_data = {"Mail": bz_user.email,
                   "Name": bz_user.name,
                   "Real Name": bz_user.real_name}

        bz_data["Created Bugzillas"] = [{"Bug ID": bz.id,
                                         "Summary": bz.summary,
                                         "Status": bz.status,
                                         "Resolution": bz.resolution,
                                         "Creation Date": str(bz.creation_time)}
                                        for bz in user_bugzillas]

        attachments = queries.get_bzattachments_by_uid(self.db, bz_user.id).all()
        ccs = queries.get_bzbugccs_by_uid(self.db, bz_user.id).all()
        comments = queries.get_bzcomments_by_uid(self.db, bz_user.id).all()
        history = queries.get_bzbughistory_by_uid(self.db, bz_user.id).all()

        bz_data["Attachments"] = [{"Bug ID": a.bug_id,
                                   "Description": a.description,
                                   "Creation Date": str(a.creation_time),
                                   "Filename": a.filename}
                                  for a in attachments]

        bz_data["CCs"] = [cc.bug_id for cc in ccs]

        bz_data["Comments"] = [{"Bug ID": c.bug_id,
                                "Comment #": c.number,
                                "Creation Date": str(c.creation_time)}
                               for c in comments]

        bz_data["History"] = [{"Bug ID": h.bug_id,
                               "Time": str(h.time),
                               "Field": h.field,
                               "Added": h.added,
                               "Removed": h.removed}
                              for h in history]

        return bz_data

    @property
    def problems(self):
        username = self.user_info['Username']
        user_problems = queries.get_problemreassigns_by_username(self.db, username).all()
        return [{"Problem": get_url("problems", problem.problem_id),
                 "Date": str(problem.date)}
                for problem in user_problems]

    @property
    def reports(self):
        username = self.user_info['Username']
        user_reports = queries.get_reportarchives_by_username(self.db, username).all()
        return [{"Report": get_url("reports", report.report_id),
                 "Date": str(report.date)}
                for report in user_reports]

    @property
    def contact_mails(self):
        contact_mail = queries.get_contact_email(self.db, self.mail)
        if contact_mail:
            reports = queries.get_reportcontactmails_by_id(self.db, contact_mail.id).all()
            return {"Contact Mail" : self.mail,
                    "Reports" : [get_url("reports", report.report_id) for report in reports]}
        return {}
