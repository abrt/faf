import json

from flask import (Blueprint, request, abort, render_template, flash,
                   redirect, url_for)
from pyfaf.storage import (PeriodicTask, TaskResult, OpSysRelease, Repo)
from webfaf_main import db

from pyfaf.celery_tasks import run_action, celery_app
from pyfaf.actions import actions as actions_all
from pyfaf.problemtypes import problemtypes
from pyfaf.opsys import systems
from pyfaf.bugtrackers import bugtrackers
from pyfaf.solutionfinders import solution_finders

from wtforms import (Form,
                     validators,
                     SelectMultipleField,
                     TextField,
                     SelectField,
                     BooleanField,
                     TextAreaField,
                     ValidationError)

from webfaf.forms import TagListField
from webfaf.utils import Pagination, admin_required
import six

url_prefix = "/celery_tasks"

celery_tasks = Blueprint("celery_tasks", __name__)

# Filter actions to exclude cmdline_only ones
actions = dict()
for n, a in actions_all.items():
    if not a.cmdline_only:
        actions[n] = a


@celery_tasks.route("/")
@admin_required
def index():
    inspect = celery_app.control.inspect()
    pts = db.session.query(PeriodicTask).order_by(PeriodicTask.id).all()
    trs = (db.session.query(TaskResult)
           .order_by(TaskResult.finished_time.desc())
           .limit(20).all())
    return render_template("celery_tasks/index.html",
                           periodic_tasks=pts,
                           task_results=trs,
                           inspect_active=inspect.active() or {},
                           inspect_scheduled=inspect.scheduled() or {},
                           actions=sorted(actions.keys()))


@celery_tasks.route("/results/<result_id>/")
@admin_required
def results_item(result_id):
    tr = db.session.query(TaskResult).get(result_id)
    if tr is None:
        raise abort(404)

    return render_template("celery_tasks/results_item.html",
                           task_result=tr)


class ActionFormArgparser(object):
    def __init__(self, F):
        self.F = F
        self.prefix_chars = "-"

    # Adapted from argparse._ActionsContainer
    # Steven J. Bethard <steven.bethard@gmail.com>
    # Licensed under the Python license
    def _get_positional_kwargs(self, dest, **kwargs):
        # make sure required is not specified
        if 'required' in kwargs:
            msg = "'required' is an invalid argument for positionals"
            raise TypeError(msg)

        # return the keyword arguments with no option strings
        return dict(kwargs, dest=dest, option_strings=[])

    # Adapted from argparse._ActionsContainer
    # Steven J. Bethard <steven.bethard@gmail.com>
    # Licensed under the Python license
    def _get_optional_kwargs(self, *args, **kwargs):
        # determine short and long option strings
        option_strings = []
        long_option_strings = []
        for option_string in args:
            # error on strings that don't start with an appropriate prefix
            if not option_string[0] in self.prefix_chars:
                msg = 'invalid option string %r: must start with a character %r'
                tup = option_string, self.prefix_chars
                raise ValueError(msg % tup)

            # strings starting with two prefix characters are long options
            option_strings.append(option_string)
            if option_string[0] in self.prefix_chars:
                if len(option_string) > 1:
                    if option_string[1] in self.prefix_chars:
                        long_option_strings.append(option_string)

        # infer destination, '--foo-bar' -> 'foo_bar' and '-x' -> 'x'
        dest = kwargs.pop('dest', None)
        if dest is None:
            if long_option_strings:
                dest_option_string = long_option_strings[0]
            else:
                dest_option_string = option_strings[0]
            dest = dest_option_string.lstrip(self.prefix_chars)
            if not dest:
                msg = 'dest= is required for options like %r'
                raise ValueError(msg % option_string)
            dest = dest.replace('-', '_')

        # return the updated keyword arguments
        return dict(kwargs, dest=dest, option_strings=option_strings)

    def add_argument(self, *args, **kwargs):
        if not args or len(args) == 1 and args[0][0] not in self.prefix_chars:
            kwargs = self._get_positional_kwargs(*args, **kwargs)
        else:
            kwargs = self._get_optional_kwargs(*args, **kwargs)

        action = kwargs.get("action", "store")
        field_args = (kwargs["dest"],)
        field_kwargs = dict(
            description=kwargs.get("help"),
            default=kwargs.get("default")
        )
        if action == "store_true":
            setattr(self.F, kwargs["dest"],
                    BooleanField(*field_args, **field_kwargs))
        else:
            if kwargs.get("nargs", "?") in "+*" or action == "append":
                field_kwargs["description"] = ((field_kwargs.get("description") or "") +
                                               " Separate multiple values by comma ','.")
                setattr(self.F, kwargs["dest"],
                        TagListField(*field_args, **field_kwargs))
            else:
                setattr(self.F, kwargs["dest"],
                        TextField(*field_args, **field_kwargs))

        self.F.argparse_fields[kwargs["dest"]] = kwargs

    def add_opsys(self, multiple=False, required=False):
        Field = SelectField
        if multiple:
            Field = SelectMultipleField
        field = Field(
            "Operating System",
            choices=((osplugin.name, osplugin.nice_name)
                     for osplugin in systems.values()))
        setattr(self.F, "opsys", field)
        self.F.argparse_fields["opsys"] = {}

    def add_problemtype(self, multiple=False):
        Field = SelectField
        if multiple:
            Field = SelectMultipleField
        field = Field(
            "Problem type",
            choices=[(a, a) for a in sorted(problemtypes.keys())])
        setattr(self.F, "problemtype", field)
        self.F.argparse_fields["problemtype"] = {}

    def add_opsys_release(self, multiple=False, required=False):
        Field = SelectField
        if multiple:
            Field = SelectMultipleField
        field = Field(
            "OS Release",
            choices=[(a[0], a[0]) for a in db.session.query(OpSysRelease.version).order_by(OpSysRelease.version)])
        setattr(self.F, "opsys_release", field)
        self.F.argparse_fields["opsys_release"] = {}

    def add_bugtracker(self, *args, **kwargs):
        field = SelectField(
            "Bugtracker",
            choices=((bt, bt) for bt in bugtrackers.keys()))
        setattr(self.F, "bugtracker", field)
        self.F.argparse_fields["bugtracker"] = {}

    def add_solutionfinder(self, *args, **kwargs):
        field = SelectField(
            "Solution finder",
            choices=((sf, sf) for sf in solution_finders.keys()))
        setattr(self.F, "solution_finder", field)
        self.F.argparse_fields["solution_finder"] = {}

    def add_repo(self, multiple=False):
        Field = SelectField
        if multiple:
            Field = SelectMultipleField
        field = Field(
            "Package repository",
            choices=[(a[0], a[0]) for a in db.session.query(Repo.name).order_by(Repo.name)])
        setattr(self.F, "NAME", field)
        self.F.argparse_fields["NAME"] = {}


class ActionFormBase(Form):
    argparse_fields = {}

    def to_cmdline_dict(self):
        res = {}
        for name, kwargs in six.iteritems(self.argparse_fields):
            data = getattr(self, name).data
            if kwargs.get("type"):
                # Call the optional type processor, e.g. int
                data = kwargs["type"](data)
            res[name] = data
        return res

    def from_cmdline_dict(self, cmdline):
        for name, kwargs in six.iteritems(self.argparse_fields):
            getattr(self, name).process_data(cmdline.get(name))


def create_action_form(action):
    # Creates a new ActionForm class based on the action cmdline
    class ActionForm(ActionFormBase):
        # to override ActionFormBase
        argparse_fields = {}

    # Mock argparser modifies the ActionForm class
    parser = ActionFormArgparser(ActionForm)
    action.tweak_cmdline_parser(parser)

    return ActionForm


class PeriodicTaskForm(Form):
    name = TextField("Name", [validators.Length(min=1, max=80)])
    enabled = BooleanField("Enabled", default=True)
    crontab_minute = TextField("Minute", [validators.Length(min=1, max=20)], description="Crontab format", default="*")
    crontab_hour = TextField("Hour", [validators.Length(min=1, max=20)], default="*")
    crontab_day_of_week = TextField("Day of week", [validators.Length(min=1, max=20)], default="*")
    crontab_day_of_month = TextField("Day of month", [validators.Length(min=1, max=20)], default="*")
    crontab_month_of_year = TextField("Month of year", [validators.Length(min=1, max=20)], default="*")


class JSONField(TextAreaField):
    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = json.loads(valuelist[0])
            except:
                self.data = None
                raise ValidationError("Not valid JSON data")
        else:
            self.data = None

    def _value(self):
        if self.data:
            try:
                return json.dumps(self.data, indent=2)
            except:
                pass
        return self.default


class PeriodicTaskFullForm(PeriodicTaskForm):
    task = TextField("Celery task", [validators.Length(min=1, max=80)])
    args = JSONField("Args", default=[])
    kwargs = JSONField("KW args", default={})


@celery_tasks.route("/action/<action_name>/", methods=("GET", "POST"))
@admin_required
def action_run(action_name):
    action = actions.get(action_name)
    if action is None:
        abort(404)
    action_form = create_action_form(action)(request.form)
    pt_form = PeriodicTaskForm(request.form)
    if request.method == "POST":
        if request.values.get("run") and action_form.validate():
            run_action.delay(action_name, action_form.to_cmdline_dict())
            flash("Action {0} started successfully.".format(action_name), "success")
            return redirect(url_for("celery_tasks.index"))
        if request.values.get("schedule") and action_form.validate() and pt_form.validate():
            pt = PeriodicTask()
            pt.task = "pyfaf.celery_tasks.run_action"
            pt.args = (action_name, action_form.to_cmdline_dict())
            pt_form.populate_obj(pt)
            db.session.add(pt)
            db.session.commit()
            flash("Action {0} scheduled successfully.".format(action_name), "success")
            return redirect(url_for("celery_tasks.index"))
    return render_template("celery_tasks/action_run.html",
                           action_name=action_name,
                           action_form=action_form,
                           schedule_form=pt_form)


@celery_tasks.route("/schedule/<int:pt_id>/", methods=("GET", "POST"))
@admin_required
def schedule_item(pt_id):
    pt = db.session.query(PeriodicTask).get(pt_id)
    if pt is None:
        abort(404)
    action = None
    action_name = None
    if pt.task == "pyfaf.celery_tasks.run_action":
        try:
            action_name = pt.args[0]
            action = actions.get(action_name)
        except:
            pass
    if action is None:
        pt_form = PeriodicTaskFullForm(request.form, pt)
        action_form = None
    else:
        pt_form = PeriodicTaskForm(request.form, pt)
        action_form = create_action_form(action)(request.form)

    if request.method == "POST":
        if request.values.get("schedule") and (action_form is None or action_form.validate()) and pt_form.validate():
            if action:
                pt.args = (action_name, action_form.to_cmdline_dict())
            pt_form.populate_obj(pt)
            db.session.commit()
            flash("Schedule item {0} saved successfully.".format(pt.name), "success")
            return redirect(url_for("celery_tasks.index"))
        elif request.values.get("delete"):
            db.session.delete(pt)
            db.session.commit()
            flash("Schedule item {0} deleted successfully.".format(pt.name), "success")
            return redirect(url_for("celery_tasks.index"))
    elif action_form is not None:
        try:
            action_form.from_cmdline_dict(pt.args[1])
        except:
            pass
    return render_template("celery_tasks/schedule_item.html",
                           pt_name=pt.name,
                           action_form=action_form,
                           schedule_form=pt_form)


@celery_tasks.route("/results/")
@admin_required
def results_list():
    pagination = Pagination(request)
    trs = (db.session.query(TaskResult)
           .order_by(TaskResult.finished_time.desc()))

    if request.args.get("unsuccessful_only", "") == "true":
        trs = trs.filter(TaskResult.state != "SUCCESS")

    if pagination.limit > 0:
        trs = trs.limit(pagination.limit)
    if pagination.offset >= 0:
        trs = trs.offset(pagination.offset)

    return render_template("celery_tasks/results_list.html",
                           task_results=trs.all(),
                           pagination=pagination)


blueprint = celery_tasks
blueprint_menu = [{
    "title": "Tasks",
    "route": "celery_tasks.index",
    "admin_required": True,
}, ]
