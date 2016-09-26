import datetime
import re
from collections import defaultdict
from operator import itemgetter
from hashlib import sha1

from flask import g

from sqlalchemy import asc, distinct

from wtforms import (Form,
                     IntegerField,
                     validators,
                     SelectMultipleField,
                     TextField,
                     SelectField,
                     FileField,
                     BooleanField)

from wtforms.ext.sqlalchemy.fields import (QuerySelectMultipleField,
                                           QuerySelectField)

from pyfaf.storage import OpSysRelease, OpSysComponent, Report, KernelTaintFlag
from pyfaf.storage.opsys import AssociatePeople, Arch
from pyfaf.problemtypes import problemtypes
from pyfaf.bugtrackers import bugtrackers
from pyfaf.queries import get_associate_by_name


class DaterangeField(TextField):
    date_format = "%Y-%m-%d"
    separator = ":"

    def __init__(self, label=None, validators=None,
                 default_days=14,
                 **kwargs):
        self.default_days = default_days
        if default_days:
            today = datetime.date.today()
            kwargs["default"] = lambda: (
                today - datetime.timedelta(days=self.default_days), today)
        super(DaterangeField, self).__init__(label, validators, **kwargs)

    def process_formdata(self, valuelist):
        if valuelist:
            s = valuelist[0].split(self.separator)
            if len(s) == 2:
                self.data = (
                    datetime.datetime.strptime(s[0], self.date_format).date(),
                    datetime.datetime.strptime(s[1], self.date_format).date())

                return

        if self.default_days:
            today = datetime.date.today()
            self.data = (
                today - datetime.timedelta(days=self. default_days), today)
        else:
            self.data = None

    def _value(self):
        if self.data:
            return self.separator.join([d.strftime(self.date_format)
                                        for d in self.data[:2]])
        else:
            return ""


class TagListField(TextField):
    def _value(self):
        if self.data:
            return u', '.join(self.data)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [x.strip() for x in valuelist[0].split(',') if len(x.strip()) > 0]
        else:
            self.data = []


def component_list():
    sub = db.session.query(distinct(Report.component_id)).subquery()
    comps = (db.session.query(OpSysComponent.id, OpSysComponent.name)
                       .filter(OpSysComponent.id.in_(sub))
                       .all())
    merged = defaultdict(list)
    for id, name in comps:
        merged[name].append(id)
    return sorted([(",".join(map(str, v)), k) for (k, v) in merged.items()],
                  key=itemgetter(1))


def component_names_to_ids(component_names):
    """
    `component_names` must be a string with comma-separated component names.
    """
    component_ids = []
    if component_names:
            component_names = map(lambda x: x.strip(),
                                  component_names.split(','))
            if len(component_names) > 0 and len(component_names[0]) > 0:
                component_ids = map(itemgetter(0),
                                    (db.session.query(OpSysComponent.id)
                                     .filter(OpSysComponent.name.in_(component_names))
                                     .all()))
    return component_ids


releases_multiselect = QuerySelectMultipleField(
    "Releases",
    query_factory=lambda: (db.session.query(OpSysRelease)
                           .filter(OpSysRelease.status != "EOL")
                           .order_by(OpSysRelease.releasedate)
                           .all()),
    get_pk=lambda a: a.id, get_label=lambda a: str(a))


arch_multiselect = QuerySelectMultipleField(
    "Architecture",
    query_factory=lambda: (db.session.query(Arch)
                           .order_by(Arch.name)
                           .all()),
    get_pk=lambda a: a.id, get_label=lambda a: str(a))


def maintainer_default():
    if g.user is not None:
        associate = get_associate_by_name(db, g.user.username)
        if associate is not None:
            return associate

associate_select = QuerySelectField(
    "Associate or Group",
    allow_blank=True,
    blank_text="Associate or Group",
    query_factory=lambda: (db.session.query(AssociatePeople)
                           .order_by(asc(AssociatePeople.name))
                           .all()),
    get_pk=lambda a: a.id, get_label=lambda a: a.name,
    default=maintainer_default)


type_multiselect = SelectMultipleField(
    "Type",
    choices=[(a, a) for a in sorted(problemtypes.keys())])

solution_checkbox = BooleanField("Solution")


class ProblemFilterForm(Form):
    opsysreleases = releases_multiselect

    component_names = TextField()

    daterange = DaterangeField(
        "Date range",
        default_days=14)

    associate = associate_select

    arch = arch_multiselect

    type = type_multiselect

    exclude_taintflags = QuerySelectMultipleField(
        "Exclude taintflags",
        query_factory=lambda: (db.session.query(KernelTaintFlag)
                               .order_by(KernelTaintFlag.character)
                               .all()),
        get_pk=lambda a: a.id, get_label=lambda a: "{0} {1}".format(a.character, a.ureport_name))

    function_names = TagListField()
    binary_names = TagListField()
    source_file_names = TagListField()

    since_version = TextField()
    since_release = TextField()

    to_version = TextField()
    to_release = TextField()

    solution = solution_checkbox

    probable_fix_osrs = QuerySelectMultipleField(
        "Probably fixed in",
        query_factory=lambda: (db.session.query(OpSysRelease)
                               .filter(OpSysRelease.status != "EOL")
                               .order_by(OpSysRelease.releasedate)
                               .all()),
        get_pk=lambda a: a.id, get_label=lambda a: str(a))

    bug_filter = SelectField("Bug status", validators=[validators.Optional()],
                             choices=[
        ("None", "Any bug status"),
        ("HAS_BUG", "Has a bug"),
        ("NO_BUGS", "No bugs"),
        ("HAS_OPEN_BUG", "Has an open bug"),
        ("ALL_BUGS_CLOSED", "All bugs closed")
    ])

    def caching_key(self):
        associate = ()
        if self.associate.data:
            associate = (self.associate.data)

        return sha1("ProblemFilterForm" + str((
            associate,
            tuple(self.arch.data or []),
            tuple(self.type.data or []),
            tuple(self.exclude_taintflags.data or []),
            tuple(sorted(self.component_names.data or [])),
            tuple(self.daterange.data or []),
            tuple(sorted(self.opsysreleases.data or [])),
            tuple(sorted(self.function_names.data or [])),
            tuple(sorted(self.binary_names.data or [])),
            tuple(sorted(self.source_file_names.data or [])),
            tuple(sorted(self.since_version.data or [])),
            tuple(sorted(self.since_release.data or [])),
            tuple(sorted(self.to_version.data or [])),
            tuple(sorted(self.to_release.data or [])),
            tuple(sorted(self.probable_fix_osrs.data or [])),
            tuple(sorted(self.bug_filter.data or [])),
            ))).hexdigest()


class ReportFilterForm(Form):
    opsysreleases = releases_multiselect

    component_names = TextField()

    first_occurrence_daterange = DaterangeField(
        "First occurrence",
        validators=[validators.Optional()],
        default_days=None)

    last_occurrence_daterange = DaterangeField(
        "Last occurrence",
        validators=[validators.Optional()],
        default_days=None)

    associate = associate_select

    arch = arch_multiselect

    type = type_multiselect

    solution = solution_checkbox

    order_by = SelectField("Order by", choices=[
        ("last_occurrence", "Last occurrence"),
        ("first_occurrence", "First occurrence"),
        ("count", "Count")],
        default="last_occurrence")

    def caching_key(self):
        associate = ()
        if self.associate.data:
            associate = (self.associate.data)

        return sha1("ReportFilterForm" + str((
            associate,
            tuple(self.arch.data or []),
            tuple(self.type.data or []),
            tuple(sorted(self.component_names.data or [])),
            tuple(self.first_occurrence_daterange.data or []),
            tuple(self.last_occurrence_daterange.data or []),
            tuple(self.order_by.data or []),
            tuple(sorted(self.opsysreleases.data or []))))).hexdigest()


class SummaryForm(Form):
    opsysreleases = releases_multiselect

    component_names = TextField()

    daterange = DaterangeField(
        "Date range",
        default_days=14)

    resolution = SelectField("Time unit", choices=[
        ("d", "daily"),
        ("w", "weekly"),
        ("m", "monthly")],
        default="d")

    def caching_key(self):
        return sha1("SummaryForm" + str((
            tuple(self.resolution.data or []),
            tuple(sorted(self.component_names.data or [])),
            tuple(self.daterange.data or []),
            tuple(sorted(self.opsysreleases.data or []))))).hexdigest()


class BacktraceDiffForm(Form):
    lhs = SelectField("LHS")
    rhs = SelectField("RHS")


class NewReportForm(Form):
    file = FileField("uReport file")


class NewAttachmentForm(Form):
    file = FileField("Attachment file")


class NewDumpDirForm(Form):
    file = FileField("Dump dir archive")


class BugIdField(TextField):
    def _value(self):
        if self.data:
            return unicode(self.data)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            for value in valuelist:
                try:
                    self.data = int(value)
                except ValueError:
                    m = re.search("id=(\d+)", value)
                    if m is None:
                        raise validators.ValidationError("Invalid Bug ID")
                    self.data = int(m.group(1))
        else:
            self.data = None


class AssociateBzForm(Form):
    bug_id = BugIdField("Bug ID or URL")
    bugtracker = SelectField("Bugtracker", choices=[
        (name, name) for name in bugtrackers.keys()])


# has to be at the end to avoid circular imports
from webfaf_main import db
