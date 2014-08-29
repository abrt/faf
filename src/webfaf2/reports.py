from operator import itemgetter
from pyfaf.storage import (Build,
                           Report,
                           OpSysComponent,
                           OpSysRelease,
                           OpSysReleaseComponent,
                           OpSysReleaseComponentAssociate,
                           Package,
                           ReportOpSysRelease,
                           ReportArch,
                           ReportPackage,
                           ReportSelinuxMode,
                           ReportHistoryDaily,
                           ReportHistoryWeekly,
                           ReportHistoryMonthly,
                           ReportUnknownPackage,
                           )
from flask import Blueprint, render_template, request, abort
from sqlalchemy import literal, desc
from utils import Pagination, diff as seq_diff


reports = Blueprint("reports", __name__)

from webfaf2 import db
from forms import ReportFilterForm


def query_reports(db, opsysrelease_ids=[], component_ids=[],
                  associate_id=None, arch_ids=[], types=[],
                  first_occurrence_since=None, first_occurrence_to=None,
                  last_occurrence_since=None, last_occurrence_to=None,
                  limit=None, offset=None, order_by="last_occurrence"):
    comp_query = (db.session.query(Report.id.label("report_id"), OpSysComponent.name.label("component"))
                            .join(ReportOpSysRelease)
                            .join(OpSysComponent)
                            .distinct(Report.id)).subquery()
    final_query = (db.session.query(Report.id,
                                    Report.first_occurrence.label("first_occurrence"),
                                    Report.last_occurrence.label("last_occurrence"),
                                    comp_query.c.component, Report.type, Report.count.label("count"))
                   .join(comp_query, Report.id == comp_query.c.report_id)
                   .order_by(desc(order_by)))

    if opsysrelease_ids:
        osr_query = (db.session.query(ReportOpSysRelease.report_id.label("report_id"))
                               .filter(ReportOpSysRelease.opsysrelease_id.in_(opsysrelease_ids))
                               .distinct(ReportOpSysRelease.report_id)
                               .subquery())
        final_query = final_query.filter(Report.id == osr_query.c.report_id)

    if component_ids:
        final_query = final_query.filter(Report.component_id.in_(component_ids))

    if arch_ids:
        arch_query = (db.session.query(ReportArch.report_id.label("report_id"))
                        .filter(ReportArch.arch_id.in_(arch_ids))
                        .distinct(ReportArch.report_id)
                        .subquery())
        final_query = final_query.filter(Report.id == arch_query.c.report_id)

    if associate_id:
        assoc_query = (db.session.query(OpSysReleaseComponent.components_id.label("components_id"))
                                 .join(OpSysReleaseComponentAssociate)
                                 .filter(OpSysReleaseComponentAssociate.associatepeople_id == associate_id)
                                 .distinct(OpSysReleaseComponent.components_id)
                                 .subquery())

        final_query = final_query.filter(Report.component_id == assoc_query.c.components_id)

    if types:
        final_query = final_query.filter(Report.type.in_(types))

    if first_occurrence_since:
        final_query = final_query.filter(Report.first_occurrence >= first_occurrence_since)
    if first_occurrence_to:
        final_query = final_query.filter(Report.first_occurrence <= first_occurrence_to)

    if last_occurrence_since:
        final_query = final_query.filter(Report.last_occurrence >= last_occurrence_since)
    if last_occurrence_to:
        final_query = final_query.filter(Report.last_occurrence <= last_occurrence_to)

    if limit > 0:
        final_query = final_query.limit(limit)
    if offset >= 0:
        final_query = final_query.offset(offset)

    return final_query.all()


@reports.route("/")
def list():
    pagination = Pagination(request)

    filter_form = ReportFilterForm(request.args)
    if filter_form.validate():
        opsysrelease_ids = [osr.id for osr in (filter_form.opsysreleases.data or [])]
        component_ids = [comp.id for comp in (filter_form.components.data or [])]
        if filter_form.associate.data:
            associate_id = filter_form.associate.data.id
        else:
            associate_id = None
        arch_ids = [arch.id for arch in (filter_form.arch.data or [])]

        types = filter_form.type.data or []

        r = query_reports(db,
                          opsysrelease_ids=opsysrelease_ids,
                          component_ids=component_ids,
                          associate_id=associate_id,
                          arch_ids=arch_ids,
                          types=types,
                          first_occurrence_since=filter_form.first_occurrence_daterange.data and filter_form.first_occurrence_daterange.data[0],
                          first_occurrence_to=filter_form.first_occurrence_daterange.data and filter_form.first_occurrence_daterange.data[1],
                          last_occurrence_since=filter_form.last_occurrence_daterange.data and filter_form.last_occurrence_daterange.data[0],
                          last_occurrence_to=filter_form.last_occurrence_daterange.data and filter_form.last_occurrence_daterange.data[1],
                          limit=pagination.limit,
                          offset=pagination.offset,
                          order_by=filter_form.order_by.data)
    else:
        r = []

    return render_template("reports/list.html",
                           reports=r,
                           filter_form=filter_form,
                           pagination=pagination)


def load_packages(db, report_id, package_type):
    build_fn = lambda prefix, column : (db.session.query(ReportPackage.id.label('%sid' % (prefix)),
                                                         Package.id.label('%spackage_id' % (prefix)),
                                                         Package.name.label('%sname' % (prefix)),
                                                         Build.version.label('%sversion' % (prefix)),
                                                         Build.release.label('%srelease' % (prefix)),
                                                         Build.epoch.label('%sepoch' % (prefix)))
                            .filter(Build.id==Package.build_id)
                            .filter(ReportPackage.report_id==report_id)
                            .filter(Package.id==column)
                            .filter(ReportPackage.type==package_type)
                            .subquery())

    installed_packages = build_fn("i", ReportPackage.installed_package_id)
    running_packages = build_fn("r", ReportPackage.running_package_id)

    known_packages = (db.session.query( ReportPackage.id,
                              installed_packages.c.ipackage_id, running_packages.c.rpackage_id,
                              installed_packages.c.iname,       running_packages.c.rname,
                              installed_packages.c.iversion,    running_packages.c.rversion,
                              installed_packages.c.irelease,    running_packages.c.rrelease,
                              installed_packages.c.iepoch,      running_packages.c.repoch,
                              ReportPackage.count)
        .outerjoin(installed_packages, ReportPackage.id==installed_packages.c.iid)
        .outerjoin(running_packages, ReportPackage.id==running_packages.c.rid)
        .filter(ReportPackage.report_id==report_id)
        .filter((installed_packages.c.iid!=None) | (running_packages.c.rid!=None)))
    unknown_packages = (db.session.query(ReportUnknownPackage.id,
                              literal(None).label("ipackage_id"), literal(None).label("rpackage_id"),
                              ReportUnknownPackage.name.label("iname"), ReportUnknownPackage.name.label("rname"),
                              ReportUnknownPackage.installed_version.label("iversion"), ReportUnknownPackage.running_version.label("rversion"),
                              ReportUnknownPackage.installed_release.label("irelease"), ReportUnknownPackage.running_release.label("rrelease"),
                              ReportUnknownPackage.installed_epoch.label("iepoch"), ReportUnknownPackage.running_epoch.label("repoch"),

                              ReportUnknownPackage.count)
        .filter(ReportUnknownPackage.type==package_type)
        .filter(ReportUnknownPackage.report_id==report_id))

    return known_packages.union(unknown_packages).all()


@reports.route("/<int:report_id>")
def item(report_id):
    result = (db.session.query(Report, OpSysComponent)
        .join(OpSysComponent)
        .filter(Report.id==report_id)
        .first())

    if result is None:
        abort(404)

    report, component = result

    releases = (db.session.query(ReportOpSysRelease, ReportOpSysRelease.count)
        .filter(ReportOpSysRelease.report_id==report_id)
        .order_by(desc(ReportOpSysRelease.count))
        .all())

    arches = (db.session.query(ReportArch, ReportArch.count)
        .filter(ReportArch.report_id==report_id)
        .order_by(desc(ReportArch.count))
        .all())

    modes = (db.session.query(ReportSelinuxMode, ReportSelinuxMode.count)
        .filter(ReportSelinuxMode.report_id==report_id)
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
        [("{0}-{1}:{2}-{3}".format(
            pkg.iname, pkg.iepoch, pkg.iversion, pkg.irelease),
         pkg.count) for pkg in related_packages],
        key=itemgetter(0))

    merged_name = dict()
    for package in related_packages:
        if package.iname in merged_name:
            merged_name[package.iname] += package.count
        else:
            merged_name[package.iname] = package.count

    related_packages_name = sorted(merged_name.items(), key=itemgetter(1),
                                   reverse=True)

    try:
        backtrace = report.backtraces[0].frames
    except:
        backtrace = []

    fid = 0
    for frame in backtrace:
        fid += 1
        frame.nice_order = fid

    return render_template("reports/item.html",
                           report=report,
                           component=component,
                           releases=releases,
                           arches=arches,
                           modes=modes,
                           daily_history=daily_history,
                           weekly_history=weekly_history,
                           monthly_history=monthly_history,
                           crashed_packages=packages,
                           related_packages_nevr=related_packages_nevr,
                           related_packages_name=related_packages_name,
                           backtrace=backtrace)


@reports.route("/diff")
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
