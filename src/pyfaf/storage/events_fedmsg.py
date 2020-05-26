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

from pyfaf.config import config
from pyfaf.utils.parse import str2bool

notify_reports = str2bool(config.get("fedmsg.realtime_reports", "false"))
notify_problems = str2bool(config.get("fedmsg.realtime_problems", "false"))

# pylint: disable=ungrouped-imports
if notify_reports or notify_problems:
    from sqlalchemy import event
    from fedora_messaging.api import publish
    from fedora_messaging.exceptions import ConnectionException, PublishReturned
    from . import Report
    from faf_schema.schema import FafReportMessage, FafProblemMessage
    from pyfaf.utils import web
    from pyfaf.common import log
    logger = log.getChild(__name__)

    levels = tuple(10**n for n in range(7))

    @event.listens_for(Report.count, "set")
    def fedmsg_report(target, value, oldvalue, initiator) -> None: # pylint: disable=unused-argument
        """
        Send Fedora Messaging notifications when Report.count reaches specified threshold.
        """
        try:
            db_report = target
            if notify_reports:
                oldcount = oldvalue
                newcount = value
                for level in levels:
                    if oldcount < level <= newcount:
                        logger.info("Notifying about report #{0} level {1}"
                                    .format(db_report.id, level))
                        msg_body = {
                            "report_id": db_report.id,
                            "function": db_report.crash_function,
                            "components": [db_report.component.name],
                            "first_occurrence": db_report.first_occurrence
                                                .strftime("%Y-%m-%d"),
                            "count": newcount,
                            "type": db_report.type,
                            "level": level,
                        }
                        if web.webfaf_installed() and db_report.hashes:
                            msg_body["url"] = web.reverse("reports.bthash_forward",
                                                          bthash=db_report.hashes[0].hash)

                        if db_report.problem_id:
                            msg_body["problem_id"] = db_report.problem_id

                        try:
                            msg = FafReportMessage(topic="faf.report.threshold{0}".format(level),
                                                   body=msg_body)
                            publish(msg)
                        except PublishReturned as e:
                            logger.exception("Fedora Messaging broker rejected message {0}: {1}".format(msg.id, e))
                        except ConnectionException as e:
                            logger.exception("Error sending message {0}: {1}".format(msg.id, e))

            if notify_problems and db_report.problem is not None:
                oldcount = db_report.problem.reports_count
                newcount = oldcount + value - oldvalue
                for level in levels:
                    if oldcount < level <= newcount:
                        logger.info("Notifying about problem #{0} level {1}"
                                    .format(db_report.problem.id, level))
                        msg_body = {
                            "problem_id": db_report.problem.id,
                            "function": db_report.problem.crash_function,
                            "components": list(db_report.problem.unique_component_names),
                            "first_occurrence": db_report.problem.first_occurrence
                                                .strftime("%Y-%m-%d"),
                            "count": newcount,
                            "type": db_report.type,
                            "level": level,
                        }
                        if web.webfaf_installed():
                            msg_body["url"] = web.reverse("problems.item", problem_id=db_report.problem.id)

                        try:
                            msg = FafProblemMessage(topic="faf.problem.threshold{0}".format(level),
                                                    body=msg_body)
                            publish(msg)
                        except PublishReturned as e:
                            logger.exception("Fedora Messaging broker rejected message {0}: {1}".format(msg.id, e))
                        except ConnectionException as e:
                            logger.exception("Error sending message {0}: {1}".format(msg.id, e))

        # Catch any exception. This is non-critical and mustn't break stuff
        # elsewhere.
        except Exception as e: # pylint: disable=broad-except
            logger.exception(e, exc_info=True)
