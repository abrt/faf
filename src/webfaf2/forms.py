import datetime
from collections import defaultdict
from operator import itemgetter

from sqlalchemy import asc, distinct

from wtforms import (Form,
                     validators,
                     SelectMultipleField,
                     TextField,
                     SelectField,
                     FileField)

from wtforms.ext.sqlalchemy.fields import (QuerySelectMultipleField,
                                           QuerySelectField)

from pyfaf.storage import OpSysRelease, OpSysComponent, Report
from pyfaf.storage.opsys import AssociatePeople, Arch
from pyfaf.problemtypes import problemtypes


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


associate_select = QuerySelectField(
    "Associate",
    allow_blank=True,
    blank_text="Associate",
    query_factory=lambda: (db.session.query(AssociatePeople)
                           .order_by(asc(AssociatePeople.name))
                           .all()),
    get_pk=lambda a: a.id, get_label=lambda a: a.name)


class ProblemFilterForm(Form):
    opsysreleases = releases_multiselect

    components = SelectMultipleField("Components")

    daterange = DaterangeField(
        "Date range",
        default_days=14)

    associate = associate_select

    arch = arch_multiselect
    # state = SelectMultipleField("State", choices=[(s, s) for s in BUG_STATES])


class ReportFilterForm(Form):
    opsysreleases = releases_multiselect

    components = SelectMultipleField("Components")

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

    type = SelectMultipleField(
        "Type",
        choices=[(a, a) for a in problemtypes.keys()])

    order_by = SelectField("Order by", choices=[
        ("last_occurrence", "Last occurrence"),
        ("first_occurrence", "First occurrence"),
        ("count", "Count")],
        default="last_occurrence")


class SummaryForm(Form):
    opsysreleases = releases_multiselect

    components = SelectMultipleField("Components")

    daterange = DaterangeField(
        "Date range",
        default_days=14)

    resolution = SelectField("Time unit", choices=[
        ("d", "daily"),
        ("w", "weekly"),
        ("m", "monthly")],
        default="d")


class BacktraceDiffForm(Form):
    lhs = SelectField("LHS")
    rhs = SelectField("RHS")


class NewReportForm(Form):
    file = FileField("uReport file")


class NewAttachmentForm(Form):
    file = FileField("Attachment file")


class NewDumpDirForm(Form):
    file = FileField("Dump dir archive")


# has to be at the end to avoid circular imports
from webfaf2_main import db
