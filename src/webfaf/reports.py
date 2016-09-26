import datetime
import logging
import json
import os
import uuid
import urllib

from collections import defaultdict
from operator import itemgetter
from pyfaf.storage import (Build,
                           BzBug,
                           ContactEmail,
                           InvalidUReport,
                           Report,
                           OpSys,
                           OpSysComponent,
                           OpSysRelease,
                           OpSysReleaseComponent,
                           OpSysReleaseComponentAssociate,
                           Package,
                           ReportBz,
                           ReportContactEmail,
                           ReportOpSysRelease,
                           ReportArch,
                           ReportPackage,
                           ReportSelinuxMode,
                           ReportHistoryDaily,
                           ReportHistoryWeekly,
                           ReportHistoryMonthly,
                           ReportUnknownPackage,
                           ReportBacktrace,
                           UnknownOpSys,
                           )
from pyfaf.queries import (get_report,
                           get_unknown_opsys,
                           user_is_maintainer,
                           get_bz_bug,
                           get_external_faf_instances,
                           get_report_opsysrelease
                           )
from pyfaf import ureport
from pyfaf.opsys import systems
from pyfaf.bugtrackers import bugtrackers
from pyfaf.config import paths
from pyfaf.ureport import ureport2
from pyfaf.solutionfinders import find_solution
from pyfaf.common import FafError
from pyfaf.problemtypes import problemtypes
from flask import (Blueprint, render_template, request, abort, redirect,
                   url_for, flash, jsonify, g)
from sqlalchemy import literal, desc, or_
from utils import (Pagination,
                   cache,
                   diff as seq_diff,
                   InvalidUsage,
                   login_required,
                   metric,
                   metric_tuple,
                   request_wants_json,
                   is_component_maintainer)


reports = Blueprint("reports", __name__)

from webfaf_main import db, flask_cache, app
from forms import (ReportFilterForm, NewReportForm, NewAttachmentForm,
                   component_names_to_ids, AssociateBzForm)


def query_reports(db, opsysrelease_ids=[], component_ids=[],
                  associate_id=None, arch_ids=[], types=[],
                  first_occurrence_since=None, first_occurrence_to=None,
                  last_occurrence_since=None, last_occurrence_to=None,
                  limit=None, offset=None, order_by="last_occurrence",
                  solution=None):

    comp_query = (db.session.query(Report.id.label("report_id"),
                                   OpSysComponent.name.label("component"))
                    .join(ReportOpSysRelease)
                    .join(OpSysComponent)
                    .distinct(Report.id)).subquery()

    bt_query = (db.session.query(Report.id.label("report_id"),
                                 ReportBacktrace.crashfn.label("crashfn"))
                          .join(ReportBacktrace)
                          .distinct(Report.id)
                          .subquery())

    final_query = (db.session.query(Report.id,
                                    Report.first_occurrence.label(
                                        "first_occurrence"),
                                    Report.last_occurrence.label(
                                        "last_occurrence"),
                                    comp_query.c.component,
                                    Report.type,
                                    Report.count.label("count"),
                                    Report.problem_id,
                                    bt_query.c.crashfn)
                   .join(comp_query, Report.id == comp_query.c.report_id)
                   .join(bt_query, Report.id == bt_query.c.report_id)
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

    if solution:
        if not solution.data:
            final_query = final_query.filter(or_(Report.max_certainty < 100, Report.max_certainty.is_(None)))

    if limit > 0:
        final_query = final_query.limit(limit)
    if offset >= 0:
        final_query = final_query.offset(offset)

    return final_query.all()


def get_reports(filter_form, pagination):
    opsysrelease_ids = [
        osr.id for osr in (filter_form.opsysreleases.data or [])]

    component_ids = component_names_to_ids(filter_form.component_names.data)

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
        order_by=filter_form.order_by.data,
        solution=filter_form.solution)

    return r


def reports_list_table_rows_cache(filter_form, pagination):
    key = ",".join((filter_form.caching_key(),
                    str(pagination.limit),
                    str(pagination.offset)))

    cached = flask_cache.get(key)
    if cached is not None:
        return cached

    r = get_reports(filter_form, pagination)

    cached = (render_template("reports/list_table_rows.html",
                              reports=r), len(r))

    flask_cache.set(key, cached, timeout=60*60)
    return cached


@reports.route("/")
def list():
    pagination = Pagination(request)

    filter_form = ReportFilterForm(request.args)
    if filter_form.validate():
        if request_wants_json():
            r = get_reports(filter_form, pagination)
        else:
            list_table_rows, report_count = \
                reports_list_table_rows_cache(filter_form, pagination)

            return render_template("reports/list.html",
                                   list_table_rows=list_table_rows,
                                   report_count=report_count,
                                   filter_form=filter_form,
                                   pagination=pagination)
    else:
        r = []

    if request_wants_json():
        return jsonify(dict(reports=r))

    return render_template("reports/list.html",
                           reports=r,
                           report_count=len(r),
                           filter_form=filter_form,
                           pagination=pagination)


def load_packages(db, report_id, package_type=None):
    def build_fn(prefix, column):
        q = (db.session.query(ReportPackage.id.label('%sid' % (prefix)),
                              Package.id.label('%spackage_id' % (prefix)),
                              Package.name.label('%sname' % (prefix)),
                              Build.version.label('%sversion' % (prefix)),
                              Build.release.label('%srelease' % (prefix)),
                              Build.epoch.label('%sepoch' % (prefix)))
             .filter(Build.id == Package.build_id)
             .filter(ReportPackage.report_id == report_id)
             .filter(Package.id == column))
        if package_type:
            q = q.filter(ReportPackage.type == package_type)

        return q.subquery()

    installed_packages = build_fn("i", ReportPackage.installed_package_id)

    known_packages = (
        db.session.query(ReportPackage.id,
                         installed_packages.c.ipackage_id,
                         installed_packages.c.iname,
                         installed_packages.c.iversion,
                         installed_packages.c.irelease,
                         installed_packages.c.iepoch,
                         ReportPackage.count)
        .outerjoin(installed_packages, ReportPackage.id ==
                   installed_packages.c.iid)
        .filter(ReportPackage.report_id == report_id)
        .filter(installed_packages.c.iid != None))

    unknown_packages = (
        db.session.query(
            ReportUnknownPackage.id,
            literal(None).label("ipackage_id"),
            ReportUnknownPackage.name.label("iname"),
            ReportUnknownPackage.version.label("iversion"),
            ReportUnknownPackage.release.label("irelease"),
            ReportUnknownPackage.epoch.label("iepoch"),
            ReportUnknownPackage.count)
        .filter(ReportUnknownPackage.report_id == report_id))
    if package_type:
        unknown_packages = unknown_packages.filter(
            ReportUnknownPackage.type == package_type)

    return known_packages.union(unknown_packages).all()


@reports.route("/<int:report_id>/")
def item(report_id):
    result = (db.session.query(Report, OpSysComponent)
              .join(OpSysComponent)
              .filter(Report.id == report_id)
              .first())

    if result is None:
        abort(404)

    report, component = result

    solutions = None

    if report.max_certainty is not None:
        osr = get_report_opsysrelease(db=db, report_id=report.id)
        solutions = [find_solution(report, db=db, osr=osr)]

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

    history_select = lambda table, date: (db.session.query(table).
                                          filter(table.report_id == report_id)
                                          # Flot is confused if not ordered
                                          .order_by(date)
                                          .all())

    daily_history = history_select(ReportHistoryDaily, ReportHistoryDaily.day)
    weekly_history = history_select(ReportHistoryWeekly, ReportHistoryWeekly.week)
    monthly_history = history_select(ReportHistoryMonthly, ReportHistoryMonthly.month)

    packages = load_packages(db, report_id)

    # creates a package_counts list with this structure:
    # [(package name, count, [(package version, count in the version)])]
    names = defaultdict(lambda: {"count": 0, "versions": defaultdict(int)})
    for pkg in packages:
        names[pkg.iname]["name"] = pkg.iname
        names[pkg.iname]["count"] += pkg.count
        names[pkg.iname]["versions"]["{0}:{1}-{2}"
            .format(pkg.iepoch, pkg.iversion, pkg.irelease)] += pkg.count

    package_counts = []
    for pkg in sorted(names.values(), key=itemgetter("count"), reverse=True):
        package_counts.append((
            pkg["name"],
            pkg["count"],
            sorted(pkg["versions"].items(), key=itemgetter(1), reverse=True)))

    try:
        backtrace = report.backtraces[0].frames
    except:
        backtrace = []

    fid = 0
    for frame in backtrace:
        fid += 1
        frame.nice_order = fid

    is_maintainer = is_component_maintainer(db, g.user, component)

    contact_emails = []
    if is_maintainer:
        contact_emails = [email_address for (email_address, ) in
                          (db.session.query(ContactEmail.email_address)
                                     .join(ReportContactEmail)
                                     .filter(ReportContactEmail.report == report))]

    forward = dict(report=report,
                   component=component,
                   releases=metric(releases),
                   arches=metric(arches),
                   modes=metric(modes),
                   daily_history=daily_history,
                   weekly_history=weekly_history,
                   monthly_history=monthly_history,
                   crashed_packages=packages,
                   package_counts=package_counts,
                   backtrace=backtrace,
                   contact_emails=contact_emails,
                   solutions=solutions)

    if request_wants_json():
        return jsonify(forward)

    forward["is_maintainer"] = is_maintainer
    forward["extfafs"] = get_external_faf_instances(db)
    return render_template("reports/item.html", **forward)


@reports.route("/<int:report_id>/associate_bz", methods=("GET", "POST"))
def associate_bug(report_id):
    result = (db.session.query(Report, OpSysComponent)
              .join(OpSysComponent)
              .filter(Report.id == report_id)
              .first())

    if result is None:
        abort(404)

    report, component = result

    is_maintainer = is_component_maintainer(db, g.user, component)

    if not is_maintainer:
        flash("You are not the maintainer of this component.", "danger")
        return redirect(url_for("reports.item", report_id=report_id))

    form = AssociateBzForm(request.form)
    if request.method == "POST" and form.validate():
        bug_id = form.bug_id.data

        reportbug = (db.session.query(ReportBz)
                     .filter(
                         (ReportBz.report_id == report.id) &
                         (ReportBz.bzbug_id == bug_id))
                     .first())

        if reportbug:
            flash("Bug already associated.", "danger")
        else:
            bug = get_bz_bug(db, bug_id)
            if not bug:
                tracker = bugtrackers[form.bugtracker.data]

                try:
                    bug = tracker.download_bug_to_storage_no_retry(db, bug_id)
                except Exception as e:
                    flash("Failed to fetch bug. {0}".format(str(e)), "danger")
                    raise

            if bug:
                new = ReportBz()
                new.report = report
                new.bzbug = bug
                db.session.add(new)
                db.session.flush()
                db.session.commit()

                flash("Bug successfully associated.", "success")
                return redirect(url_for("reports.item", report_id=report_id))
            else:
                flash("Failed to fetch bug.", "danger")

    bthash_url = url_for("reports.bthash_forward",
                         bthash=report.hashes[0].hash,
                         _external=True)
    new_bug_params = {
        "component": component.name,
        "short_desc": "[abrt] [faf] {0}: {1}(): {2} killed by {3}"
                      .format(component.name,
                              report.crash_function,
                              ",".join(exe.path for exe in report.executables),
                              report.errname
                              ),
        "comment": "This bug has been created based on an anonymous crash "
                   "report requested by the package maintainer.\n\n"
                   "Report URL: {0}"
                   .format(bthash_url),
        "bug_file_loc": bthash_url
    }

    new_bug_urls = []
    for rosr in report.opsysreleases:
        osr = rosr.opsysrelease
        for bugtracker in bugtrackers.keys():
            try:
                params = new_bug_params.copy()
                if osr.opsys.name.startswith("Red Hat"):
                    params.update(product="{0} {1}".format(osr.opsys.name,
                                                           osr.version[0]),
                                  version=osr.version)
                else:
                    params.update(product=osr.opsys.name, version=osr.version)
                new_bug_urls.append(
                    ("{0} {1} in {2}".format(osr.opsys.name, osr.version,
                                             bugtracker),
                     "{0}?{1}".format(
                        bugtrackers[bugtracker].new_bug_url,
                        urllib.urlencode(params))
                     )
                )
            except:
                pass

    return render_template("reports/associate_bug.html",
                           form=form,
                           report=report,
                           new_bug_urls=new_bug_urls)


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
    db_report = get_report(db, bthash)
    if db_report is None:
        return render_template("reports/waitforit.html"), 404

    if len(db_report.backtraces) < 1:
        return render_template("reports/waitforit.html"), 404

    return redirect(url_for("reports.item", report_id=db_report.id))


def _save_invalid_ureport(db, ureport, errormsg, reporter=None):
    try:
        new = InvalidUReport()
        new.errormsg = errormsg
        new.date = datetime.datetime.utcnow()
        new.reporter = reporter
        db.session.add(new)
        db.session.commit()

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
        db.session.commit()
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
            osr = None
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
                    solution = find_solution(report2, db=db, osr=osr)
                    if solution is not None:
                        response["message"] = (
                            "Your problem seems to be caused by {0}\n\n"
                            "{1}".format(solution.cause, solution.note_text))

                        if solution.url:
                            response["message"] += (
                                "\n\nYou can get more information at {0}"
                                .format(solution.url))

                        solution_dict = {"cause": solution.cause,
                                         "note":  solution.note_text,
                                         "url":   solution.url}
                        if not solution_dict["url"]:
                            del solution_dict["url"]
                        response["solutions"] = [solution_dict]
                        response["result"] = True

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
