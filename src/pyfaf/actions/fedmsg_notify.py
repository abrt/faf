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
import datetime
import argparse

from pyfaf.storage import Report, ReportHistoryDaily, Problem
from sqlalchemy import func, or_, and_
import fedmsg
from pyfaf.utils import web


class FedmsgNotify(Action):
    name = "fedmsg-notify"

    def __init__(self):
        super(FedmsgNotify, self).__init__()
        self.load_config_to_self("fedmsg_name", ["fedmsg.name"],
                                 "fedora-infrastructure")
        self.load_config_to_self("fedmsg_environment", ["fedmsg.environment"],
                                 "dev")

    def run(self, cmdline, db):
        levels = tuple(10**n for n in range(7))
        fedmsg.init(name=self.fedmsg_name, environment=self.fedmsg_environment)
        if cmdline.reports:
            # Sum of counts until yesterday
            q_yesterday = (
                db.session
                .query(Report.id.label("y_report_id"),
                       func.sum(ReportHistoryDaily.count).label("sum_yesterday"))
                .outerjoin(ReportHistoryDaily)
                .filter(ReportHistoryDaily.day < cmdline.date)
                .group_by(Report.id)
                .subquery()
                )
            # Sum of counts until today
            q_today = (
                db.session
                .query(Report.id.label("t_report_id"),
                       func.sum(ReportHistoryDaily.count).label("sum_today"))
                .outerjoin(ReportHistoryDaily)
                .filter(ReportHistoryDaily.day <= cmdline.date)
                .group_by(Report.id)
                .subquery()
                )
            q = (db.session.query(Report,
                                  q_today.c.sum_today,
                                  q_yesterday.c.sum_yesterday)
                 .outerjoin(q_today, Report.id == q_today.c.t_report_id)
                 .outerjoin(q_yesterday, Report.id == q_yesterday.c.y_report_id)
                 .filter(or_(Report.max_certainty.isnot(None), Report.max_certainty != 100))
                 .filter(or_(and_(q_yesterday.c.sum_yesterday == None,
                                  q_today.c.sum_today != None),
                             q_today.c.sum_today != q_yesterday.c.sum_yesterday))
                 )

            for db_report, sum_today, sum_yesterday in q.yield_per(100):
                # avoid None
                sum_yesterday = sum_yesterday or 0

                for level in levels:
                    if sum_yesterday < level and sum_today >= level:
                        self.log_info("Notifying about report #{0} level {1}"
                                      .format(db_report.id, level))
                        msg = {
                            "report_id": db_report.id,
                            "function": db_report.crash_function,
                            "components": [db_report.component.name],
                            "first_occurrence": db_report.first_occurrence
                                                .strftime("%Y-%m-%d"),
                            "count": sum_today,
                            "type": db_report.type,
                            "level": level,
                        }
                        if web.webfaf_installed():
                            msg["url"] = web.reverse("reports.item",
                                                     report_id=db_report.id)
                        if db_report.problem_id:
                            msg["problem_id"] = db_report.problem_id

                        fedmsg.publish(
                            topic="report.threshold{0}".format(level),
                            modname='faf',
                            msg=msg)

        if cmdline.problems:
            # Sum of counts until yesterday
            q_yesterday = (
                db.session
                .query(Problem.id.label("y_problem_id"),
                       func.sum(ReportHistoryDaily.count).label("sum_yesterday"))
                .join(Report)
                .outerjoin(ReportHistoryDaily)
                .filter(ReportHistoryDaily.day < cmdline.date)
                .group_by(Problem.id)
                .subquery()
                )
            # Sum of counts until today
            q_today = (
                db.session
                .query(Problem.id.label("t_problem_id"),
                       func.sum(ReportHistoryDaily.count).label("sum_today"))
                .join(Report)
                .outerjoin(ReportHistoryDaily)
                .filter(ReportHistoryDaily.day <= cmdline.date)
                .group_by(Problem.id)
                .subquery()
                )
            q = (db.session
                 .query(Problem, q_today.c.sum_today, q_yesterday.c.sum_yesterday)
                 .outerjoin(q_today, Problem.id == q_today.c.t_problem_id)
                 .outerjoin(q_yesterday, Problem.id == q_yesterday.c.y_problem_id)
                 .filter(or_(and_(q_yesterday.c.sum_yesterday == None,
                                  q_today.c.sum_today != None),
                             q_today.c.sum_today != q_yesterday.c.sum_yesterday))
                 )

            for db_problem, sum_today, sum_yesterday in q.yield_per(100):
                # avoid None
                sum_yesterday = sum_yesterday or 0

                for level in levels:
                    if sum_yesterday < level and sum_today >= level:
                        self.log_info("Notifying about problem #{0} level {1}"
                                      .format(db_problem.id, level))
                        msg = {
                            "problem_id": db_problem.id,
                            "function": db_problem.crash_function,
                            "components": db_problem.unique_component_names,
                            "first_occurrence": db_problem.first_occurrence
                                                .strftime("%Y-%m-%d"),
                            "count": sum_today,
                            "type": db_problem.type,
                            "level": level,
                        }
                        if web.webfaf_installed():
                            msg["url"] = web.reverse("problems.item",
                                                     problem_id=db_problem.id)
                        fedmsg.publish(
                            topic="problem.threshold{0}".format(level),
                            modname='faf',
                            msg=msg)

    def tweak_cmdline_parser(self, parser):
        def valid_date(s):
            try:
                return datetime.datetime.strptime(s, "%Y-%m-%d").date()
            except ValueError:
                msg = "Not a valid date: '{0}'.".format(s)
                raise argparse.ArgumentTypeError(msg)
        parser.add_argument("--date",
                            default=datetime.date.today().strftime("%Y-%m-%d"),
                            type=valid_date,
                            help="Date")
        parser.add_argument("--reports", action="store_true",
                            default=False, help="Notify about reports")
        parser.add_argument("--problems", action="store_true",
                            default=False, help="Notify about problems")
