import datetime
import logging
import json
import os
import uuid
import urllib
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from collections import defaultdict
from operator import itemgetter

from pyfaf.storage import (AssociatePeople,
                           Build,
                           BzBug,
                           ContactEmail,
                           InvalidUReport,
                           Report,
                           OpSys,
                           OpSysComponent,
                           OpSysRelease,
                           OpSysComponentAssociate,
                           Package,
                           ReportHash,
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
                           ReportArchive,
                           ReportExecutable,
                           UnknownOpSys,
                           ProblemOpSysRelease,
                           Problem,
                          )
from pyfaf.queries import (get_report,
                           get_unknown_opsys,
                           get_bz_bug,
                           get_external_faf_instances,
                           get_report_opsysrelease,
                           get_crashed_package_for_report,
                           get_crashed_unknown_package_nevr_for_report
                          )
from pyfaf import ureport
from pyfaf.opsys import systems
from pyfaf.bugtrackers import bugtrackers
from pyfaf.config import paths
from pyfaf.ureport import ureport2
from pyfaf.solutionfinders import find_solution
from pyfaf.common import FafError
from pyfaf.problemtypes import problemtypes
from pyfaf import queries
from flask import (Blueprint, render_template, request, abort, redirect,
                   url_for, flash, jsonify, g)
from sqlalchemy import literal, desc, or_
from sqlalchemy.exc import SQLAlchemyError
from webfaf.utils import (Pagination,
                          diff as seq_diff,
                          InvalidUsage,
                          metric,
                          request_wants_json,
                          is_component_maintainer)


reports = Blueprint("reports", __name__)

from webfaf.webfaf_main import db, flask_cache
from webfaf.forms import (ReportFilterForm, NewReportForm, NewAttachmentForm,
                          component_names_to_ids, AssociateBzForm)


def query_reports(db, opsysrelease_ids=[], component_ids=[],
                  associate_id=None, arch_ids=[], types=[],
                  occurrence_since=None, occurrence_to=None,
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

    final_query = (db.session.query(Report, bt_query.c.crashfn)
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
                OpSysComponent.id.label("components_id"))
            .join(OpSysComponentAssociate)
            .filter(OpSysComponentAssociate.associatepeople_id ==
                    associate_id)
            .distinct(OpSysComponent.id)
            .subquery())

        final_query = final_query.filter(
            Report.component_id == assoc_query.c.components_id)

    if types:
        final_query = final_query.filter(Report.type.in_(types))

    if occurrence_since:
        final_query = final_query.filter(
            Report.last_occurrence >= occurrence_since)
    if occurrence_to:
        final_query = final_query.filter(
            Report.first_occurrence <= occurrence_to)

    if solution:
        if not solution.data:
            final_query = final_query.filter(or_(Report.max_certainty < 100, Report.max_certainty.is_(None)))

    if limit > 0:
        final_query = final_query.limit(limit)
    if offset >= 0:
        final_query = final_query.offset(offset)

    report_tuples = final_query.all()
    for report, crashfn in report_tuples:
        report.crashfn = crashfn

    return [x[0] for x in report_tuples]


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
    if filter_form.daterange.data:
        (since_date, to_date) = filter_form.daterange.data
    else:
        since_date = None
        to_date = None

    r = query_reports(
        db,
        opsysrelease_ids=opsysrelease_ids,
        component_ids=component_ids,
        associate_id=associate_id,
        arch_ids=arch_ids,
        types=types,
        occurrence_since=since_date,
        occurrence_to=to_date,
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
def dashboard():
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


@reports.route("/items/", methods=['PUT', 'POST'])
def items():
    data = dict()

    if request.method == "POST":
        post_data = request.get_json()
    else:
        return abort(405)

    for report_hash in post_data:
        report = (db.session.query(Report)
                  .join(ReportHash)
                  .filter(ReportHash.hash == report_hash)
                  .first())

        if report is not None:
            data[report_hash] = item(report.id, True)

    return jsonify(data)


@reports.route("/get_hash/", endpoint="get_hash")
@reports.route("/get_hash/<os>/", endpoint="os")
@reports.route("/get_hash/<os>/<release>", endpoint="release")
@reports.route("/get_hash/<os>/<release>/<since>", endpoint="since")
@reports.route("/get_hash/<os>/<release>/<since>/<to>", endpoint="to")
def get_hash(os=None, release=None, since=None, to=None):
    if to:
        to = datetime.datetime.strptime(to, "%Y-%m-%d")
        since = datetime.datetime.strptime(since, "%Y-%m-%d")

        report_hash = queries.get_all_report_hashes(db, opsys=os,
                                                    opsys_releases=release,
                                                    date_from=since,
                                                    date_to=to)

    elif since:
        since = datetime.datetime.strptime(since, "%Y-%m-%d")

        report_hash = queries.get_all_report_hashes(db, opsys=os,
                                                    opsys_releases=release,
                                                    date_from=since)

    elif release:
        report_hash = queries.get_all_report_hashes(db, opsys=os,
                                                    opsys_releases=release)

    elif os:
        report_hash = queries.get_all_report_hashes(db, opsys=os)
    else:
        report_hash = queries.get_all_report_hashes(db)

    r_hash = []

    for item in report_hash:
        r_hash.append(item.hash)

    if request_wants_json():
        return jsonify({"data": r_hash})
    else:
        abort(405)


@reports.route("/<int:report_id>/")
def item(report_id, want_object=False):
    result = (db.session.query(Report, OpSysComponent)
              .join(OpSysComponent)
              .filter(Report.id == report_id)
              .first())

    if result is None:
        abort(404)

    report, component = result

    executable = (db.session.query(ReportExecutable.path)
                  .filter(ReportExecutable.report_id == report_id)
                  .first())
    if executable:
        executable = executable[0]
    else:
        executable = "unknown"


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

    history_select = lambda table, date, date_range: (db.session.query(table).
                                                      filter(table.report_id == report_id)
                                                      .filter(date >= date_range)
                                                      # Flot is confused if not ordered
                                                      .order_by(date)
                                                      .all())

    MAX_DAYS = 20  # Default set on 20
    MAX_WEEK = 20  # Default set on 20
    MAX_MONTH = 20  # Default set on 20

    today = datetime.date.today()

    # Show only 20 days
    daily_history = history_select(ReportHistoryDaily, ReportHistoryDaily.day,
                                   (today - timedelta(days=MAX_DAYS)))

    if len(daily_history) == 0:
        for x in range(0, MAX_DAYS):
            daily_history.append({'day': today - timedelta(x),
                                  'count': 0,
                                  'opsysrelease_id': releases[0].ReportOpSysRelease.opsysrelease_id})

    elif len(daily_history) < MAX_DAYS:
        if daily_history[-1].day < (today):
            daily_history.append({'day': today,
                                  'count': 0,
                                  'opsysrelease_id': releases[0].ReportOpSysRelease.opsysrelease_id
                                 })

        if daily_history[0].day > (today - timedelta(MAX_DAYS)):
            daily_history.append({'day': today - timedelta(MAX_DAYS),
                                  'count': 0,
                                  'opsysrelease_id': releases[0].ReportOpSysRelease.opsysrelease_id
                                 })

    # Show only 20 weeks
    last_monday = datetime.datetime.today() - timedelta(datetime.datetime.today().weekday())

    weekly_history = history_select(ReportHistoryWeekly, ReportHistoryWeekly.week,
                                    (last_monday - timedelta(days=MAX_WEEK*7)))
    if len(weekly_history) == 0:
        for x in range(0, MAX_WEEK):
            weekly_history.append({'week': last_monday - timedelta(x*7),
                                   'count': 0,
                                   'opsysrelease_id': releases[0].ReportOpSysRelease.opsysrelease_id})
    elif len(weekly_history) < MAX_WEEK:
        if weekly_history[-1].week < (last_monday.date()):
            weekly_history.append({'week': last_monday,
                                   'count': 0,
                                   'opsysrelease_id': releases[0].ReportOpSysRelease.opsysrelease_id})

        if weekly_history[0].week > ((last_monday - timedelta(7*MAX_WEEK)).date()):
            weekly_history.append({'week': last_monday - timedelta(7*MAX_WEEK),
                                   'count': 0,
                                   'opsysrelease_id': releases[0].ReportOpSysRelease.opsysrelease_id})

    # Show only 20 months
    monthly_history = history_select(ReportHistoryMonthly, ReportHistoryMonthly.month,
                                     (today - relativedelta(months=MAX_MONTH)))

    first_day_of_month = lambda t: (datetime.date(t.year, t.month, 1))

    fdom = first_day_of_month(datetime.datetime.today())

    if len(monthly_history) == 0:
        for x in range(0, MAX_MONTH):
            monthly_history.append({'month': fdom - relativedelta(months=x),
                                    'count': 0,
                                    'opsysrelease_id': releases[0].ReportOpSysRelease.opsysrelease_id})

    elif len(monthly_history) < MAX_MONTH:
        if monthly_history[-1].month < (fdom):
            monthly_history.append({'month': fdom,
                                    'count': 0,
                                    'opsysrelease_id': releases[0].ReportOpSysRelease.opsysrelease_id})

        if monthly_history[0].month > (fdom - relativedelta(months=MAX_MONTH)):
            monthly_history.append({'month': fdom - relativedelta(months=MAX_MONTH),
                                    'count': 0,
                                    'opsysrelease_id': releases[0].ReportOpSysRelease.opsysrelease_id})

    complete_history = history_select(ReportHistoryMonthly, ReportHistoryMonthly.month,
                                      (datetime.datetime.strptime('1970-01-01', '%Y-%m-%d')))

    unique_ocurrence_os = {}
    if len(complete_history) > 0:
        for ch in complete_history:
            os_name = "{0} {1}".format(ch.opsysrelease.opsys.name, ch.opsysrelease.version)

            if ch.count is None:
                ch.count = 0

            if ch.unique is None:
                ch.count = 0

            if os_name not in unique_ocurrence_os:
                unique_ocurrence_os[os_name] = {'count': ch.count, 'unique': ch.unique}
            else:
                unique_ocurrence_os[os_name]['count'] += ch.count
                unique_ocurrence_os[os_name]['unique'] += ch.unique

    sorted(unique_ocurrence_os)

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

    maintainer = (db.session.query(AssociatePeople)
                  .join(OpSysComponentAssociate)
                  .join(OpSysComponent)
                  .filter(OpSysComponent.name == component.name)).first()

    maintainer_contact = ""
    if maintainer:
        maintainer_contact = maintainer.name

    probably_fixed = (db.session.query(ProblemOpSysRelease, Build)
                      .join(Problem)
                      .join(Report)
                      .join(Build)
                      .filter(Report.id == report_id)
                      .first())

    unpackaged = not (get_crashed_package_for_report(db, report.id) or
                      get_crashed_unknown_package_nevr_for_report(db, report.id))

    forward = dict(report=report,
                   executable=executable,
                   probably_fixed=probably_fixed,
                   component=component,
                   releases=metric(releases),
                   arches=metric(arches),
                   modes=metric(modes),
                   daily_history=daily_history,
                   weekly_history=weekly_history,
                   monthly_history=monthly_history,
                   complete_history=complete_history,
                   unique_ocurrence_os=unique_ocurrence_os,
                   crashed_packages=packages,
                   package_counts=package_counts,
                   backtrace=backtrace,
                   contact_emails=contact_emails,
                   unpackaged=unpackaged,
                   solutions=solutions,
                   maintainer_contact=maintainer_contact)

    forward['error_name'] = report.error_name
    forward['oops'] = report.oops

    if want_object:
        try:
            cf = component.name
            if len(report.backtraces[0].crash_function) > 0:
                cf += " in {0}".format(report.backtraces[0].crash_function)
            forward['crash_function'] = cf
        except:
            forward['crash_function'] = ""

        if probably_fixed:
            tmp_dict = probably_fixed.ProblemOpSysRelease.serialize
            tmp_dict['probable_fix_build'] = probably_fixed.Build.serialize

            forward['probably_fixed'] = tmp_dict
        # Avg count occurrence from first to last occurence
        forward['avg_count_per_month'] = get_avg_count(report.first_occurrence,
                                                       report.last_occurrence,
                                                       report.count)

        if len(forward['report'].bugs) > 0:
            forward['bugs'] = []
            for bug in forward['report'].bugs:
                try:
                    forward['bugs'].append(bug.serialize)
                except:
                    print("Bug serialize failed")
        return forward

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
                if str(exp) == 'uReport must contain affected package':
                    raise InvalidUsage(("Server is not accepting problems "
                                        "from unpackaged files."), 400)
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
                    ureport.validate(report2)
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


@reports.route("/<int:report_id>/archive.json", methods=["POST"])
def archive(report_id):
    data = request.get_json()
    response = {"status": "success",
                "username": g.user.username,
                "date": datetime.date.today()}
    try:
        report = db.session.query(Report).filter_by(id=report_id).first()
        if data["activate"]:
            if report.archive:
                report.archive.active = True
                report.archive.date = response["date"]
                report.archive.username = response["username"]
            else:
                db.session.add(ReportArchive(date=response["date"],
                                             active=True,
                                             report_id=report_id,
                                             username=response["username"]))
            db.session.commit()
        else:
            if report.archive:
                report.archive.active = False
                db.session.commit()
    except SQLAlchemyError:
        response["status"] = "failure"

    return jsonify(response)


def get_avg_count(first, last, count):
    diff = last - first
    r_d = diff.days / 30.4  # avg month size
    if r_d < 1:
        r_d = 1

    return int(round(count / r_d))
