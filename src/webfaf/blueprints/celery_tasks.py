import json
from flask import (Blueprint, request, abort, render_template, flash,
                   redirect, url_for)
from wtforms import (Form,
                     validators,
                     SelectMultipleField,
                     TextField,
                     SelectField,
                     BooleanField,
                     TextAreaField,
                     FileField,
                     ValidationError)

from pyfaf.storage import (ExternalFafInstance, PeriodicTask, TaskResult, OpSys, OpSysRelease, Repo, Arch)
from pyfaf.celery_tasks import run_action, celery_app
from pyfaf.actions import actions as actions_all
from pyfaf.problemtypes import problemtypes
from pyfaf.opsys import systems
from pyfaf.bugtrackers import bugtrackers
from pyfaf.solutionfinders import solution_finders

from webfaf_main import db
from webfaf.forms import TagListField
from webfaf.utils import Pagination, admin_required

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


class ActionFormArgparser():
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
                raise ValueError(msg % dest_option_string)
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
            default=kwargs.get("default"),
            validators=[]
        )
        if action == "store_true":
            setattr(self.F, kwargs["dest"],
                    BooleanField(*field_args, **field_kwargs))
        else:
            if kwargs.get("validators"):
                for (vld, vld_kwargs) in kwargs.get("validators"):
                    vld_class = getattr(validators, vld)
                    field_kwargs["validators"].append(vld_class(**vld_kwargs))
            else:
                field_kwargs["validators"].append(validators.Optional())

            if kwargs.get("nargs", "?") in "+*" or action == "append":
                field_kwargs["description"] = ((field_kwargs.get("description") or "") +
                                               " Separate multiple values by comma ','.")
                setattr(self.F, kwargs["dest"],
                        TagListField(*field_args, **field_kwargs))
            else:
                setattr(self.F, kwargs["dest"],
                        TextField(*field_args, **field_kwargs))

        self.F.argparse_fields[kwargs["dest"]] = kwargs

    def add_argument_group(self):
        return ActionFormArgGroup(self.F)

    def add_opsys(self, multiple=False, required=False, positional=False, with_rel=False, helpstr=None): # pylint: disable=unused-argument
        if required:
            vs = [validators.Required()]
        else:
            vs = [validators.Optional()]

        choice_lst = [(osplugin.name, osplugin.nice_name) for osplugin in systems.values()]
        arg_str = "opsys"

        if positional:
            arg_str = "OPSYS"

            q = db.session.query(OpSys.name)
            choice_lst = [(a[0], a[0]) for a in q]

            if with_rel:
                q = q.join(OpSysRelease).with_entities(OpSys.name, OpSysRelease.version)
                choice_lst = [(a[0] + " " + a[1], a[0] + " " + a[1]) for a in q]

        Field = SelectField
        if multiple:
            Field = SelectMultipleField
        field = Field(
            "Operating System",
            vs,
            choices=choice_lst)
        setattr(self.F, arg_str, field)
        self.F.argparse_fields[arg_str] = {}

    def add_opsys_rel_status(self, required=False):
        if required:
            vs = [validators.Required()]
        else:
            vs = [validators.Optional()]

        field = SelectField(
            "Release status",
            vs,
            choices=[(a, a) for a in ["ACTIVE", "UNDER_DEVELOPMENT", "EOL"]])
        setattr(self.F, "status", field)
        self.F.argparse_fields["status"] = {}

    def add_arch(self, multiple=False, required=False, positional=False, helpstr=None): # pylint: disable=unused-argument
        if required:
            vs = [validators.Required()]
        else:
            vs = [validators.Optional()]

        arg_str = "arch"
        if positional:
            arg_str = "ARCH"

        Field = SelectField
        if multiple:
            Field = SelectMultipleField

        q = db.session.query(Arch.name).order_by(Arch.name)

        field = Field(
            "Architecture",
            vs,
            choices=[(a[0], a[0]) for a in q])
        setattr(self.F, arg_str, field)
        self.F.argparse_fields[arg_str] = {}

    def add_problemtype(self, multiple=False):
        Field = SelectField
        if multiple:
            Field = SelectMultipleField
        field = Field(
            "Problem type",
            choices=[(a, a) for a in sorted(problemtypes.keys())])
        setattr(self.F, "problemtype", field)
        self.F.argparse_fields["problemtype"] = {}

    def add_opsys_release(self, multiple=False, required=False, positional=False, helpstr=None): # pylint: disable=unused-argument
        if required:
            vs = [validators.Required()]
        else:
            vs = [validators.Optional()]

        Field = SelectField
        if multiple:
            Field = SelectMultipleField

        q = db.session.query(OpSysRelease.version).order_by(OpSysRelease.version)

        field = Field(
            "OS Release",
            vs,
            choices=[(a[0], a[0]) for a in q])

        arg_str = "opsys_release"
        if positional:
            arg_str = "RELEASE"

        setattr(self.F, arg_str, field)
        self.F.argparse_fields[arg_str] = {}

    def add_bugtracker(self, *args, **kwargs): # pylint: disable=unused-argument
        field = SelectField(
            "Bugtracker",
            choices=[(bt, bt) for bt in bugtrackers])
        setattr(self.F, "bugtracker", field)
        self.F.argparse_fields["bugtracker"] = {}

    def add_solutionfinder(self, *args, **kwargs): # pylint: disable=unused-argument
        field = SelectField(
            "Solution finder",
            choices=[(sf, sf) for sf in solution_finders])
        setattr(self.F, "solution_finder", field)
        self.F.argparse_fields["solution_finder"] = {}

    def add_repo(self, multiple=False, helpstr=None): # pylint: disable=unused-argument

        Field = SelectField
        if multiple:
            Field = SelectMultipleField

        q = db.session.query(Repo.name).order_by(Repo.name)

        field = Field(
            "Package repository",
            choices=[(a[0], a[0]) for a in q])
        setattr(self.F, "REPO", field)
        self.F.argparse_fields["REPO"] = {}

    def add_repo_type(self, choices=None, required=False, positional=False, helpstr=None): # pylint: disable=unused-argument
        if required:
            vs = [validators.Required()]
        else:
            vs = [validators.Optional()]

        field = SelectField(
            "Repository type",
            vs,
            choices=[(a, a) for a in choices])

        arg_str = "type"
        if positional:
            arg_str = "TYPE"

        setattr(self.F, arg_str, field)
        self.F.argparse_fields[arg_str] = {}

    def add_ext_instance(self, multiple=False, helpstr=None): # pylint: disable=unused-argument

        Field = SelectField
        if multiple:
            Field = SelectMultipleField

        q = db.session.query(ExternalFafInstance) \
            .with_entities(ExternalFafInstance.id, ExternalFafInstance.name) \
            .order_by(ExternalFafInstance.id)

        field = Field(
            "External FAF instance",
            choices=[(a[0], str(a[0]) + " " + a[1]) for a in q],
            coerce=int)

        setattr(self.F, "INSTANCE_ID", field)
        self.F.argparse_fields["INSTANCE_ID"] = {}

    def add_file(self, required=False, helpstr=None): # pylint: disable=unused-argument
        if required:
            vs = [validators.Required()]
        else:
            vs = [validators.Optional()]

        field = FileField(
            "Repository file",
            vs)

        setattr(self.F, "FILE", field)
        self.F.argparse_fields["FILE"] = {}

    def add_gpgcheck_toggle(self, required=False, helpstr=None): # pylint: disable=unused-argument
        if required:
            vs = [validators.Required()]
        else:
            vs = [validators.Optional()]

        field = SelectField(
            "New GPG check requirement",
            vs,
            choices=[(a, a) for a in ["leave as is", "enable", "disable"]])
        setattr(self.F, "gpgcheck", field)
        self.F.argparse_fields["gpgcheck"] = {}

class ActionFormArgGroup(ActionFormArgparser):
    def __init__(self, F, mutually_exclusive=False): # pylint: disable=super-init-not-called
        self.F = F
        self.mutually_exclusive = mutually_exclusive
        self.prefix_chars = "-"
        self.grouped_args = {}


class ActionFormBase(Form):
    argparse_fields = {}

    def to_cmdline_dict(self):
        res = {}
        for name, kwargs in self.argparse_fields.items():
            data = getattr(self, name).data
            if kwargs.get("type"):
                # Call the optional type processor, e.g. int
                data = kwargs["type"](data)
            res[name] = data
        return res

    def from_cmdline_dict(self, cmdline):
        for name in self.argparse_fields:
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


# custom TextField to avoid clashing field names in ActionForm and PeriodicTaskForm
# which breaks form validation for extfafmod and repoadd
class TaskNameField(TextField):
    def __init__(self, label="", _name="", **kwargs):
        super(TaskNameField, self).__init__(label, _name="task_name", **kwargs)

class PeriodicTaskForm(Form):
    name = TaskNameField("Name", validators=[validators.Length(min=1, max=80)])
    enabled = BooleanField("Enabled", default="checked")
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
            except: # pylint: disable=bare-except
                self.data = None
                raise ValidationError("Not valid JSON data")
        else:
            self.data = None

    def _value(self):
        if self.data:
            try:
                return json.dumps(self.data, indent=2)
            except: # pylint: disable=bare-except
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
        except: # pylint: disable=bare-except
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
        if request.values.get("delete"):
            db.session.delete(pt)
            db.session.commit()
            flash("Schedule item {0} deleted successfully.".format(pt.name), "success")
            return redirect(url_for("celery_tasks.index"))
    if action_form is not None:
        try:
            action_form.from_cmdline_dict(pt.args[1])
        except: # pylint: disable=bare-except
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
