# Copyright (C) 2013  ABRT Team
# Copyright (C) 2013  Red Hat, Inc.
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

from pyfaf.bugtrackers import bugtrackers
from pyfaf.checker import (Checker,
                           DictChecker,
                           IntChecker,
                           ListChecker,
                           StringChecker)
from pyfaf.common import FafError, log
from pyfaf.config import config
from pyfaf.opsys import systems
from pyfaf.problemtypes import problemtypes
from pyfaf.queries import (get_arch_by_name,
                           get_bz_bug,
                           get_reportbz_by_major_version,
                           get_component_by_name,
                           get_contact_email,
                           get_history_day,
                           get_history_month,
                           get_history_week,
                           get_osrelease,
                           get_mantis_bug,
                           get_report,
                           get_report_contact_email,
                           get_reportarch,
                           get_reportreason,
                           get_reportosrelease,
                           get_reportbz)
from pyfaf.storage import (Arch,
                           ContactEmail,
                           OpSysComponent,
                           OpSysRelease,
                           Report,
                           ReportBz,
                           ReportArch,
                           ReportComment,
                           ReportContactEmail,
                           ReportHash,
                           ReportHistoryDaily,
                           ReportHistoryMonthly,
                           ReportHistoryWeekly,
                           ReportOpSysRelease,
                           ReportMantis,
                           ReportReason,
                           ReportURL,
                           column_len)
from pyfaf.ureport_compat import ureport1to2
from sqlalchemy.exc import IntegrityError

log = log.getChildLogger(__name__)

__all__ = ["get_version", "save", "ureport2",
           "validate", "validate_attachment"]


UREPORT_CHECKER = DictChecker({
    "os":              DictChecker({
        "name":            StringChecker(allowed=list(systems.keys())),
        "version":         StringChecker(pattern=r"^[a-zA-Z0-9_\.\-\+~]+$",
                                         maxlen=column_len(OpSysRelease,
                                                           "version")),
        "architecture":    StringChecker(pattern=r"^[a-zA-Z0-9_]+$",
                                         maxlen=column_len(Arch, "name")),
        # Anything else will be checked by the plugin
    }),

    # The checker for packages depends on operating system
    "packages":        ListChecker(Checker(object)),

    "problem":         DictChecker({
        "type":            StringChecker(allowed=list(problemtypes.keys())),
        # Anything else will be checked by the plugin
    }),

    "reason":          StringChecker(maxlen=column_len(ReportReason, "reason")),

    "reporter":        DictChecker({
        "name":            StringChecker(pattern=r"^[a-zA-Z0-9 ]+$", maxlen=64),
        "version":         StringChecker(pattern=r"^[a-zA-Z0-9_\.\- ]+$",
                                         maxlen=64),
    }),

    "ureport_version": IntChecker(minval=0),
})


ATTACHMENT_CHECKER = DictChecker({
    "bthash": StringChecker(pattern=r"^[a-fA-F0-9]+$", maxlen=256),
    "type": StringChecker(maxlen=64),
    "data": StringChecker(maxlen=1024),
})


def get_version(ureport):
    """
    Get uReport version
    """

    ver = 0
    if "ureport_version" in ureport:
        try:
            ver = int(ureport["ureport_version"])
        except ValueError:
            raise FafError("`ureport_version` must be an integer")

    return ver


def validate_ureport1(ureport):
    """
    Validates uReport1
    """

    ureport2 = ureport1to2(ureport)
    validate_ureport2(ureport2)


def validate_ureport2(ureport):
    """
    Validates uReport2
    """

    UREPORT_CHECKER.check(ureport)

    osplugin = systems[ureport["os"]["name"]]
    osplugin.validate_ureport(ureport["os"])
    osplugin.validate_packages(ureport["packages"])

    problemplugin = problemtypes[ureport["problem"]["type"]]
    problemplugin.validate_ureport(ureport["problem"])

    return True


def validate(ureport):
    """
    Validates ureport based on ureport_version element
    """

    ver = get_version(ureport)

    if ver == 1:
        return validate_ureport1(ureport)

    if ver == 2:
        return validate_ureport2(ureport)

    raise FafError("uReport version {0} is not supported".format(ver))


def save_ureport1(db, ureport, create_component=False, timestamp=None, count=1):
    """
    Saves uReport1
    """

    ureport2 = ureport1to2(ureport)
    validate(ureport2)
    save_ureport2(db, ureport2, create_component=create_component,
                  timestamp=timestamp, count=count)


def save_ureport2(db, ureport, create_component=False, timestamp=None, count=1):
    """
    Save uReport2
    """
    if timestamp is None:
        timestamp = datetime.datetime.utcnow()

    osplugin = systems[ureport["os"]["name"]]
    problemplugin = problemtypes[ureport["problem"]["type"]]

    db_osrelease = get_osrelease(db, osplugin.nice_name,
                                 ureport["os"]["version"])
    if db_osrelease is None:
        raise FafError("Operating system '{0} {1}' not found in storage"
                       .format(osplugin.nice_name, ureport["os"]["version"]))

    report_hash = problemplugin.hash_ureport(ureport["problem"])
    db_report = get_report(db, report_hash)
    if db_report is None:
        component_name = problemplugin.get_component_name(ureport["problem"])
        db_component = get_component_by_name(db, component_name,
                                             osplugin.nice_name)
        if db_component is None:
            if create_component:
                log.info("Creating an unsupported component '{0}' in "
                         "operating system '{1}'".format(component_name,
                                                         osplugin.nice_name))
                db_component = OpSysComponent()
                db_component.name = component_name
                db_component.opsys = db_osrelease.opsys
                db.session.add(db_component)
            else:
                raise FafError("Unknown component '{0}' in operating system "
                               "{1}".format(component_name, osplugin.nice_name))

        db_report = Report()
        db_report.type = problemplugin.name
        db_report.first_occurrence = timestamp
        db_report.last_occurrence = timestamp
        db_report.count = 0
        db_report.component = db_component
        db.session.add(db_report)

        db_report_hash = ReportHash()
        db_report_hash.report = db_report
        db_report_hash.hash = report_hash
        db.session.add(db_report_hash)

    if db_report.first_occurrence > timestamp:
        db_report.first_occurrence = timestamp

    if db_report.last_occurrence < timestamp:
        db_report.last_occurrence = timestamp

    db_reportosrelease = get_reportosrelease(db, db_report, db_osrelease)
    if db_reportosrelease is None:
        db_reportosrelease = ReportOpSysRelease()
        db_reportosrelease.report = db_report
        db_reportosrelease.opsysrelease = db_osrelease
        db_reportosrelease.count = 0
        db.session.add(db_reportosrelease)

    db_reportosrelease.count += count

    db_arch = get_arch_by_name(db, ureport["os"]["architecture"])
    if db_arch is None:
        raise FafError("Architecture '{0}' is not supported"
                       .format(ureport["os"]["architecture"]))

    db_reportarch = get_reportarch(db, db_report, db_arch)
    if db_reportarch is None:
        db_reportarch = ReportArch()
        db_reportarch.report = db_report
        db_reportarch.arch = db_arch
        db_reportarch.count = 0
        db.session.add(db_reportarch)

    db_reportarch.count += count

    reason = ureport["reason"].encode("utf-8")
    db_reportreason = get_reportreason(db, db_report, reason)
    if db_reportreason is None:
        db_reportreason = ReportReason()
        db_reportreason.report = db_report
        db_reportreason.reason = reason
        db_reportreason.count = 0
        db.session.add(db_reportreason)

    db_reportreason.count += count

    day = timestamp.date()
    db_daily = get_history_day(db, db_report, db_osrelease, day)
    if db_daily is None:
        db_daily = ReportHistoryDaily()
        db_daily.report = db_report
        db_daily.opsysrelease = db_osrelease
        db_daily.day = day
        db_daily.count = 0
        db_daily.unique = 0
        db.session.add(db_daily)

    if "serial" in ureport["problem"] and ureport["problem"]["serial"] == 1:
        db_daily.unique += 1
    db_daily.count += count

    week = day - datetime.timedelta(days=day.weekday())
    db_weekly = get_history_week(db, db_report, db_osrelease, week)
    if db_weekly is None:
        db_weekly = ReportHistoryWeekly()
        db_weekly.report = db_report
        db_weekly.opsysrelease = db_osrelease
        db_weekly.week = week
        db_weekly.count = 0
        db_weekly.unique = 0
        db.session.add(db_weekly)

    if "serial" in ureport["problem"] and ureport["problem"]["serial"] == 1:
        db_weekly.unique += 1
    db_weekly.count += count

    month = day.replace(day=1)
    db_monthly = get_history_month(db, db_report, db_osrelease, month)
    if db_monthly is None:
        db_monthly = ReportHistoryMonthly()
        db_monthly.report = db_report
        db_monthly.opsysrelease = db_osrelease
        db_monthly.month = month
        db_monthly.count = 0
        db_monthly.unique = 0
        db.session.add(db_monthly)

    if "serial" in ureport["problem"] and ureport["problem"]["serial"] == 1:
        db_monthly.unique += 1
    db_monthly.count += count

    osplugin.save_ureport(db, db_report, ureport["os"], ureport["packages"],
                          count=count)
    problemplugin.save_ureport(db, db_report, ureport["problem"], count=count)

    # Update count as last, so that handlers listening to its "set" event have
    # as much information as possible
    db_report.count += count

    db.session.flush()

    problemplugin.save_ureport_post_flush()


def save(db, ureport, create_component=False, timestamp=None, count=1):
    """
    Save uReport based on ureport_version element assuming the given uReport "
    is valid. Flush the database at the end.
    """

    if timestamp is None:
        timestamp = datetime.datetime.utcnow()

    ver = get_version(ureport)

    if ver == 1:
        save_ureport1(db, ureport, create_component=create_component,
                      timestamp=timestamp, count=count)
    elif ver == 2:
        save_ureport2(db, ureport, create_component=create_component,
                      timestamp=timestamp, count=count)
    else:
        raise FafError("uReport version {0} is not supported".format(ver))

    db.session.flush()


def ureport2(ureport):
    """
    Takes `ureport` and converts it to uReport2 if necessary.
    """

    ver = get_version(ureport)

    if ver == 1:
        return ureport1to2(ureport)
    elif ver == 2:
        return ureport

    raise FafError("uReport version {0} is not supported".format(ver))


def validate_attachment(attachment):
    """
    Validate uReport attachment.
    """

    ATTACHMENT_CHECKER.check(attachment)
    return True


def attachment_type_allowed(atype):
    """
    Return True if `atype` attachment type is allowed in config
    """

    allowed = config['ureport.acceptattachments']
    if allowed == '*':
        return True

    return atype in allowed


def save_attachment(db, attachment):
    atype = attachment["type"].lower()

    if not attachment_type_allowed(atype):
        raise FafError("Attachment type '{}' not allowed on this server"
                       .format(atype))

    report = get_report(db, attachment["bthash"])
    if not report:
        raise FafError("Report for given bthash not found")

    if atype in ["rhbz", "fedora-bugzilla", "rhel-bugzilla"]:
        bug_id = int(attachment["data"])

        reportbug = (db.session.query(ReportBz)
                     .filter(
                         (ReportBz.report_id == report.id) &
                         (ReportBz.bzbug_id == bug_id)
                     )
                     .first())

        if reportbug:
            log.debug("Skipping existing attachment")
            return

        bug = get_bz_bug(db, bug_id)
        if not bug:
            if atype in bugtrackers:
                # download from bugtracker identified by atype
                tracker = bugtrackers[atype]

                if not tracker.installed(db):
                    raise FafError("Bugtracker used in this attachment"
                                   " is not installed")

                bug = tracker.download_bug_to_storage(db, bug_id)
            elif atype == "rhbz":
                # legacy value
                # - we need to guess the bugtracker:
                # either fedora-bugzilla or rhel-bugzilla,
                # former is more probable
                for possible_tracker in ["fedora-bugzilla", "rhel-bugzilla"]:
                    if possible_tracker not in bugtrackers:
                        continue

                    tracker = bugtrackers[possible_tracker]
                    if not tracker.installed(db):
                        continue

                    bug = tracker.download_bug_to_storage(db, bug_id)
                    if bug:
                        break

        if bug:
            new = ReportBz()
            new.report = report
            new.bzbug = bug
            db.session.add(new)
            db.session.flush()
        else:
            log.error("Failed to fetch bug #{0} from '{1}'"
                      .format(bug_id, atype))

    elif atype == "centos-mantisbt":
        bug_id = int(attachment["data"])

        reportbug = (db.session.query(ReportMantis)
                     .filter(
                         (ReportMantis.report_id == report.id) &
                         (ReportMantis.mantisbug_id == bug_id))
                     .first())

        if reportbug:
            log.debug("Skipping existing attachment")
            return

        bug = get_mantis_bug(db, bug_id)
        if not bug:
            if atype in bugtrackers:
                # download from bugtracker identified by atype
                tracker = bugtrackers[atype]

                if not tracker.installed(db):
                    raise FafError("Bugtracker used in this attachment"
                                   " is not installed")

                bug = tracker.download_bug_to_storage(db, bug_id)

        if bug:
            new = ReportMantis()
            new.report = report
            new.mantisbug = bug
            db.session.add(new)
            db.session.flush()
        else:
            log.error("Failed to fetch bug #{0} from '{1}'"
                      .format(bug_id, atype))

    elif atype == "comment":
        comment = ReportComment()
        comment.report = report
        comment.text = attachment["data"]
        comment.saved = datetime.datetime.utcnow()
        db.session.add(comment)
        db.session.flush()

    elif atype == "email":
        db_contact_email = get_contact_email(db, attachment["data"])
        if db_contact_email is None:
            db_contact_email = ContactEmail()
            db_contact_email.email_address = attachment["data"]
            db.session.add(db_contact_email)

            db_report_contact_email = ReportContactEmail()
            db_report_contact_email.contact_email = db_contact_email
            db_report_contact_email.report = report
            db.session.add(db_report_contact_email)
        else:
            db_report_contact_email = \
                get_report_contact_email(db, db_contact_email.id, report.id)
            if db_report_contact_email is None:
                db_report_contact_email = ReportContactEmail()
                db_report_contact_email.contact_email = db_contact_email
                db_report_contact_email.report = report
                db.session.add(db_report_contact_email)

        try:
            db.session.flush()
        except IntegrityError:
            raise FafError("Email address already assigned to the report")

    elif atype == "url":
        url = attachment["data"]

        # 0ne URL can be attached to many Reports, but every reports must
        # have unique url's
        db_url = (db.session.query(ReportURL)
                  .filter(ReportURL.url == url)
                  .filter(ReportURL.report_id == report.id)
                  .first())

        if db_url:
            log.debug("Skipping existing URL")
            return

        db_url = ReportURL()
        db_url.report = report
        db_url.url = url
        db_url.saved = datetime.datetime.utcnow()

        try:
            db.session.flush()
        except IntegrityError:
            raise FafError("Unable to save URL")

    else:
        log.warning("Unknown attachment type")


def valid_known_type(known_type):
    """
    Check if all "known" values from configuration file are correct
    allowed_known_type is list with allowed values
    """
    allowed_known_type = ['EQUAL_UREPORT_EXISTS', 'BUG_OS_MINOR_VERSION',
                          'BUG_OS_MAJOR_VERSION']

    for ktype in known_type:
        if ktype not in allowed_known_type and ktype.strip() != "":
            log.error("Known type '{0}' is not supported by FAF Server"
                      .format(ktype))
            return False

    return True


def is_known(ureport, db, return_report=False, opsysrelease_id=None):
    ureport = ureport2(ureport)
    validate(ureport)

    problemplugin = problemtypes[ureport["problem"]["type"]]
    report_hash = problemplugin.hash_ureport(ureport["problem"])

    known_type = []

    # Split allowed types from config
    if 'ureport.known' in config and config['ureport.known'].strip() != "":
        known_type = config['ureport.known'].strip().split(" ")

    if len(known_type) > 0 and not valid_known_type(known_type):
        return None

    report_os = {'name':None,
                 'version':None,
                 'architecture':None}

    if 'EQUAL_UREPORT_EXISTS' in known_type:
        report_os = ureport["os"]

    report = get_report(db, report_hash, os_name=report_os['name'], os_version=report_os['version'],
                        os_arch=report_os['architecture'])

    if report is None:
        return None

    found = False

    if 'EQUAL_UREPORT_EXISTS' in known_type:

        found = True

    elif ('BUG_OS_MINOR_VERSION' in known_type and
          get_reportbz(db, report.id, opsysrelease_id).first() is not None):

        found = True
    elif ('BUG_OS_MAJOR_VERSION' in known_type and
          get_reportbz_by_major_version(db, report.id,
                                        major_version=ureport["os"]["version"]
                                        .split(".")[0])
          .first() is not None):

        found = True

    elif not known_type:
        bzs = get_reportbz(db, report.id, opsysrelease_id).all()
        for bz in bzs:
            if not bz.bzbug.private:
                found = True
                break

    if found:
        if return_report:
            return report
        return True
    else:
        return None
