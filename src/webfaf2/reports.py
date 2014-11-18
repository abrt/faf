import datetime
import logging
import json
import os
import uuid

from operator import itemgetter
from pyfaf.storage import (Build,
                           BzBug,
                           InvalidUReport,
                           Report,
                           OpSys,
                           OpSysComponent,
                           OpSysRelease,
                           OpSysReleaseComponent,
                           OpSysReleaseComponentAssociate,
                           Package,
                           ReportBz,
                           ReportOpSysRelease,
                           ReportArch,
                           ReportPackage,
                           ReportSelinuxMode,
                           ReportHistoryDaily,
                           ReportHistoryWeekly,
                           ReportHistoryMonthly,
                           ReportUnknownPackage,
                           UnknownOpSys,
                           )
from pyfaf.queries import get_report_by_hash, get_unknown_opsys
from pyfaf import ureport
from pyfaf.opsys import systems
from pyfaf.config import paths
from pyfaf.ureport import ureport2
from pyfaf.solutionfinders import find_solution
from pyfaf.common import FafError
from pyfaf.problemtypes import problemtypes
from flask import (Blueprint, render_template, request, abort, redirect,
                   url_for, flash, jsonify)
from sqlalchemy import literal, desc
from utils import (Pagination,
                   cache,
                   diff as seq_diff,
                   InvalidUsage,
                   metric,
                   metric_tuple,
                   request_wants_json)


reports = Blueprint("reports", __name__)

from webfaf2_main import db
from forms import (ReportFilterForm, NewReportForm, NewAttachmentForm,
                   component_list)


def query_reports(db, opsysrelease_ids=[], component_ids=[],
                  associate_id=None, arch_ids=[], types=[],
                  first_occurrence_since=None, first_occurrence_to=None,
                  last_occurrence_since=None, last_occurrence_to=None,
                  limit=None, offset=None, order_by="last_occurrence"):

    comp_query = (db.session.query(Report.id.label("report_id"),
                                   OpSysComponent.name.label("component"))
                    .join(ReportOpSysRelease)
                    .join(OpSysComponent)
                    .distinct(Report.id)).subquery()

    final_query = (db.session.query(Report.id,
                                    Report.first_occurrence.label(
                                        "first_occurrence"),
                                    Report.last_occurrence.label(
                                        "last_occurrence"),
                                    comp_query.c.component,
                                    Report.type,
                                    Report.count.label("count"))
                   .join(comp_query, Report.id == comp_query.c.report_id)
                   .order_by(desc(order_by)))

    if opsysrelease_ids:
        osr_query = (
            db.session.query(ReportOpSysRelease.report_id.label("report_id"))
            .filter(ReportOpSysRelease.opsysrelease_id.in_(opsysrelease_ids))
            .distinct(ReportOpSysRelease.report_id)
            .subquery())
        final_query = final_query.filter(Report.id == osr_query.c.report_id)

    if component_ids:
        final_query = final_query.filter(
            Report.component_id.in_(component_ids))

    if arch_ids:
        arch_query = (db.session.query(ReportArch.report_id.label("report_id"))
                        .filter(ReportArch.arch_id.in_(arch_ids))
                        .distinct(ReportArch.report_id)
                        .subquery())
        final_query = final_query.filter(Report.id == arch_query.c.report_id)

    if associate_id:
        assoc_query = (
            db.session.query(
                OpSysReleaseComponent.components_id.label("components_id"))
            .join(OpSysReleaseComponentAssociate)
            .filter(OpSysReleaseComponentAssociate.associatepeople_id ==
                    associate_id)
            .distinct(OpSysReleaseComponent.components_id)
            .subquery())

        final_query = final_query.filter(
            Report.component_id == assoc_query.c.components_id)

    if types:
        final_query = final_query.filter(Report.type.in_(types))

    if first_occurrence_since:
        final_query = final_query.filter(
            Report.first_occurrence >= first_occurrence_since)
    if first_occurrence_to:
        final_query = final_query.filter(
            Report.first_occurrence <= first_occurrence_to)

    if last_occurrence_since:
        final_query = final_query.filter(
            Report.last_occurrence >= last_occurrence_since)
    if last_occurrence_to:
        final_query = final_query.filter(
            Report.last_occurrence <= last_occurrence_to)

    if limit > 0:
        final_query = final_query.limit(limit)
    if offset >= 0:
        final_query = final_query.offset(offset)

    return final_query.all()


@reports.route("/")
@cache(hours=1)
def list():
    pagination = Pagination(request)

    filter_form = ReportFilterForm(request.args)
    filter_form.components.choices = component_list()
    if filter_form.validate():
        opsysrelease_ids = [
            osr.id for osr in (filter_form.opsysreleases.data or [])]

        component_ids = []
        for comp in filter_form.components.data or []:
            component_ids += map(int, comp.split(','))

        if filter_form.associate.data:
            associate_id = filter_form.associate.data.id
        else:
            associate_id = None
        arch_ids = [arch.id for arch in (filter_form.arch.data or [])]

        types = filter_form.type.data or []

        r = query_reports(
            db,
            opsysrelease_ids=opsysrelease_ids,
            component_ids=component_ids,
            associate_id=associate_id,
            arch_ids=arch_ids,
            types=types,
            first_occurrence_since=filter_form.first_occurrence_daterange.data
            and filter_form.first_occurrence_daterange.data[0],
            first_occurrence_to=filter_form.first_occurrence_daterange.data
            and filter_form.first_occurrence_daterange.data[1],
            last_occurrence_since=filter_form.last_occurrence_daterange.data
            and filter_form.last_occurrence_daterange.data[0],
            last_occurrence_to=filter_form.last_occurrence_daterange.data
            and filter_form.last_occurrence_daterange.data[1],
            limit=pagination.limit,
            offset=pagination.offset,
            order_by=filter_form.order_by.data)
    else:
        r = []

    if request_wants_json():
        return jsonify(dict(reports=r))

    return render_template("reports/list.html",
                           reports=r,
                           filter_form=filter_form,
                           pagination=pagination)


def load_packages(db, report_id, package_type):
    build_fn = lambda prefix, column: (
        db.session.query(ReportPackage.id.label('%sid' % (prefix)),
                         Package.id.label('%spackage_id' % (prefix)),
                         Package.name.label('%sname' % (prefix)),
                         Build.version.label('%sversion' % (prefix)),
                         Build.release.label('%srelease' % (prefix)),
                         Build.epoch.label('%sepoch' % (prefix)))
        .filter(Build.id == Package.build_id)
        .filter(ReportPackage.report_id == report_id)
        .filter(Package.id == column)
        .filter(ReportPackage.type == package_type)
        .subquery())

    installed_packages = build_fn("i", ReportPackage.installed_package_id)
    running_packages = build_fn("r", ReportPackage.running_package_id)

    known_packages = (
        db.session.query(ReportPackage.id,
                         installed_packages.c.ipackage_id,
                         running_packages.c.rpackage_id,
                         installed_packages.c.iname,
                         running_packages.c.rname,
                         installed_packages.c.iversion,
                         running_packages.c.rversion,
                         installed_packages.c.irelease,
                         running_packages.c.rrelease,
                         installed_packages.c.iepoch,
                         running_packages.c.repoch,
                         ReportPackage.count)
        .outerjoin(installed_packages, ReportPackage.id ==
                   installed_packages.c.iid)
        .outerjoin(running_packages, ReportPackage.id ==
                   running_packages.c.rid)
        .filter(ReportPackage.report_id == report_id)
        .filter((installed_packages.c.iid != None) |
                (running_packages.c.rid != None)))

    unknown_packages = (
        db.session.query(
            ReportUnknownPackage.id,
            literal(None).label("ipackage_id"),
            literal(None).label("rpackage_id"),
            ReportUnknownPackage.name.label("iname"),
            ReportUnknownPackage.name.label("rname"),
            ReportUnknownPackage.installed_version.label("iversion"),
            ReportUnknownPackage.running_version.label("rversion"),
            ReportUnknownPackage.installed_release.label("irelease"),
            ReportUnknownPackage.running_release.label("rrelease"),
            ReportUnknownPackage.installed_epoch.label("iepoch"),
            ReportUnknownPackage.running_epoch.label("repoch"),
            ReportUnknownPackage.count)
        .filter(ReportUnknownPackage.type == package_type)
        .filter(ReportUnknownPackage.report_id == report_id))

    return known_packages.union(unknown_packages).all()


@reports.route("/<int:report_id>/")
@cache(hours=1)
def item(report_id):
    result = (db.session.query(Report, OpSysComponent)
              .join(OpSysComponent)
              .filter(Report.id == report_id)
              .first())

    if result is None:
        abort(404)

    report, component = result

    releases = (db.session.query(ReportOpSysRelease, ReportOpSysRelease.count)
                .filter(ReportOpSysRelease.report_id == report_id)
                .order_by(desc(ReportOpSysRelease.count))
                .all())

    arches = (db.session.query(ReportArch, ReportArch.count)
              .filter(ReportArch.report_id == report_id)
              .order_by(desc(ReportArch.count))
              .all())

    modes = (db.session.query(ReportSelinuxMode, ReportSelinuxMode.count)
             .filter(ReportSelinuxMode.report_id == report_id)
             .order_by(desc(ReportSelinuxMode.count))
             .all())

    history_select = lambda table: (db.session.query(table).
                                    filter(table.report_id == report_id)
                                    .all())

    daily_history = history_select(ReportHistoryDaily)
    weekly_history = history_select(ReportHistoryWeekly)
    monthly_history = history_select(ReportHistoryMonthly)

    packages = load_packages(db, report_id, "CRASHED")
    related_packages = load_packages(db, report_id, "RELATED")
    related_packages_nevr = sorted(
        [metric_tuple(name="{0}-{1}:{2}-{3}".format(
            pkg.iname, pkg.iepoch, pkg.iversion, pkg.irelease),
            count=pkg.count) for pkg in related_packages],
        key=itemgetter(0))

    merged_name = dict()
    for package in related_packages:
        if package.iname in merged_name:
            merged_name[package.iname] += package.count
        else:
            merged_name[package.iname] = package.count

    related_packages_name = sorted([metric_tuple(name=item[0], count=item[1])
                                    for item in merged_name.items()],
                                   key=itemgetter(0),
                                   reverse=True)

    try:
        backtrace = report.backtraces[0].frames
    except:
        backtrace = []

    fid = 0
    for frame in backtrace:
        fid += 1
        frame.nice_order = fid

    forward = dict(report=report,
                   component=component,
                   releases=metric(releases),
                   arches=metric(arches),
                   modes=metric(modes),
                   daily_history=daily_history,
                   weekly_history=weekly_history,
                   monthly_history=monthly_history,
                   crashed_packages=packages,
                   related_packages_nevr=related_packages_nevr,
                   related_packages_name=related_packages_name,
                   backtrace=backtrace)

    if request_wants_json():
        return jsonify(forward)

    return render_template("reports/item.html", **forward)


@reports.route("/diff/")
def diff():
    lhs_id = int(request.args.get('lhs', 0))
    rhs_id = int(request.args.get('rhs', 0))

    lhs = (db.session.query(Report)
                     .filter(Report.id == lhs_id)
                     .first())

    rhs = (db.session.query(Report)
                     .filter(Report.id == rhs_id)
                     .first())

    if lhs is None or rhs is None:
        abort(404)

    frames_diff = seq_diff(lhs.backtraces[0].frames,
                           rhs.backtraces[0].frames,
                           lambda lhs, rhs:
                           lhs.symbolsource.symbol == rhs.symbolsource.symbol)

    return render_template("reports/diff.html",
                           diff=frames_diff,
                           lhs={'id': lhs_id, 'type': lhs.type},
                           rhs={'id': rhs_id, 'type': rhs.type})


@reports.route("/bthash/<bthash>/")
def bthash_forward(bthash):
    db_report = get_report_by_hash(db, bthash)
    if db_report is None:
        abort(404)

    if len(db_report.backtraces) < 1:
        return render_template("reports/waitforit.html")

    return redirect(url_for("reports.item", report_id=db_report.id))


def _save_invalid_ureport(db, ureport, errormsg, reporter=None):
    try:
        new = InvalidUReport()
        new.errormsg = errormsg
        new.date = datetime.datetime.utcnow()
        new.reporter = reporter
        db.session.add(new)
        db.session.flush()

        new.save_lob("ureport", ureport)
    except Exception as ex:
        logging.error(str(ex))


def _save_unknown_opsys(db, opsys):
    try:
        name = opsys.get("name")
        version = opsys.get("version")

        db_unknown_opsys = get_unknown_opsys(db, name, version)
        if db_unknown_opsys is None:
            db_unknown_opsys = UnknownOpSys()
            db_unknown_opsys.name = name
            db_unknown_opsys.version = version
            db_unknown_opsys.count = 0
            db.session.add(db_unknown_opsys)

        db_unknown_opsys.count += 1
        db.session.flush()
    except Exception as ex:
        logging.error(str(ex))


@reports.route("/new/", methods=('GET', 'POST'))
def new():
    form = NewReportForm()
    if request.method == "POST":
        try:
            if not form.validate() or form.file.name not in request.files:
                raise InvalidUsage("Invalid form data.", 400)
            raw_data = request.files[form.file.name].read()
            try:
                data = json.loads(raw_data)
            except Exception as ex:
                _save_invalid_ureport(db, raw_data, str(ex))
                raise InvalidUsage("Couldn't parse JSON data.", 400)

            try:
                ureport.validate(data)
            except Exception as exp:
                reporter = None
                if ("reporter" in data and
                        "name" in data["reporter"] and
                        "version" in data["reporter"]):
                    reporter = "{0} {1}".format(data["reporter"]["name"],
                                                data["reporter"]["version"])

                _save_invalid_ureport(db, json.dumps(data, indent=2),
                                      str(exp), reporter=reporter)

                if ("os" in data and
                        "name" in data["os"] and
                        data["os"]["name"] not in systems and
                        data["os"]["name"].lower() not in systems):
                    _save_unknown_opsys(db, data["os"])

                raise InvalidUsage("uReport data is invalid.", 400)

            report = data

            max_ureport_length = InvalidUReport.__lobs__["ureport"]

            if len(str(report)) > max_ureport_length:
                raise InvalidUsage("uReport may only be {0} bytes long"
                                   .format(max_ureport_length), 413)

            osr_id = None
            if report["os"]["name"] in systems:
                osr = (db.session.query(OpSysRelease)
                       .join(OpSys)
                       .filter(OpSys.name ==
                               systems[report["os"]["name"]].nice_name)
                       .filter(OpSysRelease.version ==
                               report["os"]["version"])
                       .first())

                if osr:
                    osr_id = osr.id
            try:
                dbreport = ureport.is_known(report, db, return_report=True,
                                            opsysrelease_id=osr_id)
            except Exception as e:
                logging.exception(e)
                dbreport = None

            known = bool(dbreport)
            fname = str(uuid.uuid4())
            fpath = os.path.join(paths["reports_incoming"], fname)
            with open(fpath, 'w') as file:
                file.write(raw_data)

            if request_wants_json():
                response = {'result': known}

                try:
                    report2 = ureport2(report)
                except FafError:
                    report2 = None

                if report2 is not None:
                    solution = find_solution(report2, db=db)
                    if solution is not None:
                        response['message'] = (
                            "Your problem seems to be caused by {0}\n\n"
                            "{1}".format(solution.cause, solution.note_text))

                        if solution.url:
                            response['message'] += (
                                "\n\nYou can get more information at {0}"
                                .format(solution.url))

                        response['solutions'] = [{'cause': solution.cause,
                                                  'note':  solution.note_text,
                                                  'url':   solution.url}]
                        response['result'] = True

                    try:
                        problemplugin = problemtypes[
                            report2["problem"]["type"]]
                        response["bthash"] = problemplugin.hash_ureport(
                            report2["problem"])
                    except Exception as e:
                        logging.exception(e)
                        pass

                if known:
                    url = url_for('reports.item', report_id=dbreport.id,
                                  _external=True)
                    parts = [{"reporter": "ABRT Server",
                              "value": url,
                              "type": "url"}]

                    bugs = (db.session.query(BzBug)
                                      .join(ReportBz)
                                      .filter(ReportBz.bzbug_id == BzBug.id)
                                      .filter(ReportBz.report_id == dbreport.id)
                                      .all())
                    for bug in bugs:
                        parts.append({"reporter": "Bugzilla",
                                      "value": bug.url,
                                      "type": "url"})

                    if 'message' not in response:
                        response['message'] = ''
                    else:
                        response['message'] += '\n\n'

                    response[
                        'message'] += "\n".join(p["value"] for p in parts
                                                if p["type"].lower() == "url")
                    response['reported_to'] = parts

                json_response = jsonify(response)
                json_response.status_code = 202
                return json_response
            else:
                flash(
                    "The uReport was saved successfully. Thank you.", "success")
                return render_template("reports/new.html",
                                       form=form), 202

        except InvalidUsage as e:
            if request_wants_json():
                response = jsonify({"error": e.message})
                response.status_code = e.status_code
                return response
            else:
                flash(e.message, "danger")
                return render_template("reports/new.html",
                                       form=form), e.status_code

    return render_template("reports/new.html",
                           form=form)


@reports.route("/attach/", methods=("GET", "POST"))
def attach():
    form = NewAttachmentForm()
    if request.method == "POST":
        try:
            if not form.validate() or form.file.name not in request.files:
                raise InvalidUsage("Invalid form data.", 400)
            raw_data = request.files[form.file.name].read()

            try:
                data = json.loads(raw_data)
            except:
                raise InvalidUsage("Invalid JSON file", 400)

            try:
                ureport.validate_attachment(data)
            except Exception as ex:
                raise InvalidUsage("Validation failed: %s" % ex, 400)

            attachment = data

            max_attachment_length = 2048

            if len(str(attachment)) > max_attachment_length:
                err = "uReport attachment may only be {0} bytes long" \
                      .format(max_attachment_length)
                raise InvalidUsage(err, 413)

            fname = str(uuid.uuid4())
            fpath = os.path.join(paths["attachments_incoming"], fname)
            with open(fpath, "w") as file:
                file.write(raw_data)

            if request_wants_json():
                json_response = jsonify({"result": True})
                json_response.status_code = 202
                return json_response
            else:
                flash("The attachment was saved successfully. Thank you.",
                      "success")
                return render_template("reports/attach.html",
                                       form=form), 202

        except InvalidUsage as e:
            if request_wants_json():
                response = jsonify({"error": e.message})
                response.status_code = e.status_code
                return response
            else:
                flash(e.message, "danger")
                return render_template("reports/attach.html",
                                       form=form), e.status_code

    return render_template("reports/attach.html",
                           form=form)
