import datetime
from operator import itemgetter
from pyfaf.storage import (Arch,
                           OpSysComponent,
                           OpSysRelease,
                           OpSysReleaseComponent,
                           OpSysReleaseComponentAssociate,
                           Package,
                           Problem,
                           ProblemComponent,
                           Report,
                           ReportArch,
                           ReportExecutable,
                           ReportHash,
                           ReportOpSysRelease,
                           ReportPackage,
                           ReportUnknownPackage)
from pyfaf.queries import get_history_target, get_report_by_hash

from flask import Blueprint, render_template, request, abort, url_for, redirect

from sqlalchemy import desc, func

problems = Blueprint("problems", __name__)

from webfaf2 import db
from forms import ProblemFilterForm, BacktraceDiffForm, component_list
from utils import Pagination


def query_problems(db, hist_table, hist_column,
                   opsysrelease_ids=[], component_ids=[],
                   associate_id=None, arch_ids=[],
                   rank_filter_fn=None, post_process_fn=None,
                   limit=None, offset=None):
    """
    Return problems ordered by history counts
    """

    rank_query = (db.session.query(Problem.id.label('id'),
                                   func.sum(hist_table.count).label('rank'))
                  .join(Report)
                  .join(hist_table))
    if opsysrelease_ids:
        rank_query = rank_query.filter(
            hist_table.opsysrelease_id.in_(opsysrelease_ids))

    if rank_filter_fn:
        rank_query = rank_filter_fn(rank_query)

    rank_query = rank_query.group_by(Problem.id).subquery()

    final_query = (
        db.session.query(Problem,
                         rank_query.c.rank.label('count'),
                         rank_query.c.rank)
        .filter(rank_query.c.id == Problem.id)
        .order_by(desc(rank_query.c.rank)))

    if component_ids:
        comp_query = (
            db.session.query(ProblemComponent.problem_id.label('problem_id'))
            .filter(ProblemComponent.component_id.in_(component_ids))
            .distinct(ProblemComponent.problem_id)
            .subquery())

        final_query = final_query.filter(Problem.id == comp_query.c.problem_id)

    if associate_id:
        assoc_query = (
            db.session.query(ProblemComponent.problem_id.label('problem_id'))
            .join(OpSysComponent)
            .join(OpSysReleaseComponent)
            .join(OpSysReleaseComponentAssociate)
            .filter(
                OpSysReleaseComponentAssociate.associatepeople_id ==
                associate_id)
            .subquery())

        final_query = final_query.filter(
            Problem.id == assoc_query.c.problem_id)

    if arch_ids:
        arch_query = (
            db.session.query(Report.problem_id.label('problem_id'))
            .join(ReportArch)
            .filter(ReportArch.arch_id.in_(arch_ids))
            .distinct(Report.problem_id)
            .subquery())

        final_query = final_query.filter(Problem.id == arch_query.c.problem_id)

    if limit > 0:
        final_query = final_query.limit(limit)
    if offset >= 0:
        final_query = final_query.offset(offset)

    problem_tuples = final_query.all()

    if post_process_fn:
        problem_tuples = post_process_fn(problem_tuples)

    for problem, count, rank in problem_tuples:
        problem.count = count

    return [x[0] for x in problem_tuples]


@problems.route("/")
def list():
    pagination = Pagination(request)

    filter_form = ProblemFilterForm(request.args)
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

        (since_date, to_date) = filter_form.daterange.data
        date_delta = to_date - since_date
        if date_delta < datetime.timedelta(days=16):
            resolution = "daily"
        elif date_delta < datetime.timedelta(weeks=10):
            resolution = "weekly"
        else:
            resolution = "monthly"
        hist_table, hist_field = get_history_target(resolution)

        p = query_problems(db,
                           hist_table,
                           hist_field,
                           opsysrelease_ids=opsysrelease_ids,
                           component_ids=component_ids,
                           associate_id=associate_id,
                           arch_ids=arch_ids,
                           rank_filter_fn=lambda query: (
                               query.filter(hist_field >= since_date)
                                    .filter(hist_field <= to_date)),
                           limit=pagination.limit,
                           offset=pagination.offset)
    else:
        p = []

    return render_template("problems/list.html",
                           problems=p,
                           filter_form=filter_form,
                           pagination=pagination,
                           url_next_page=pagination.url_next_page(len(p)),
                           url_prev_page=pagination.url_prev_page())


@problems.route("/<int:problem_id>")
def item(problem_id):
    problem = db.session.query(Problem).filter(
        Problem.id == problem_id).first()

    if problem is None:
        raise abort(404)

    report_ids = [report.id for report in problem.reports]

    sub = (db.session.query(ReportOpSysRelease.opsysrelease_id,
                            func.sum(ReportOpSysRelease.count).label("cnt"))
           .join(Report)
           .filter(Report.id.in_(report_ids))
           .group_by(ReportOpSysRelease.opsysrelease_id)
           .order_by(desc("cnt"))
           .subquery())

    osreleases = db.session.query(OpSysRelease, sub.c.cnt).join(sub).all()

    sub = (db.session.query(ReportArch.arch_id,
                            func.sum(ReportArch.count).label("cnt"))
           .join(Report)
           .filter(Report.id.in_(report_ids))
           .group_by(ReportArch.arch_id)
           .order_by(desc("cnt"))
           .subquery())

    arches = (db.session.query(Arch, sub.c.cnt).join(sub)
                        .order_by(desc("cnt"))
                        .all())

    exes = (db.session.query(ReportExecutable.path,
                             func.sum(ReportExecutable.count).label("cnt"))
            .join(Report)
            .filter(Report.id.in_(report_ids))
            .group_by(ReportExecutable.path)
            .order_by(desc("cnt"))
            .all())

    sub = (db.session.query(ReportPackage.installed_package_id,
                            func.sum(ReportPackage.count).label("cnt"))
           .join(Report)
           .filter(Report.id.in_(report_ids))
           .group_by(ReportPackage.installed_package_id)
           .order_by(desc("cnt"))
           .subquery())
    packages_known = db.session.query(Package, sub.c.cnt).join(sub).all()

    packages_unknown = (db.session.query(ReportUnknownPackage,
                                         ReportUnknownPackage.count)
                                  .join(Report)
                                  .filter(Report.id.in_(report_ids))).all()

    packages = packages_known + packages_unknown

    packages_nevr = [(pkg.nevr(), cnt) for (pkg, cnt) in packages]

    # merge packages with different architectures
    merged_nevr = dict()
    for package, count in packages_nevr:
        if package in merged_nevr:
            merged_nevr[package] += count
        else:
            merged_nevr[package] = count

    packages_nevr = sorted(merged_nevr.items(), key=itemgetter(0, 1))

    packages_name = [(pkg.name, cnt) for (pkg, cnt) in packages]

    # merge packages with different EVRA
    merged_name = dict()
    for package, count in packages_name:
        if package in merged_name:
            merged_name[package] += count
        else:
            merged_name[package] = count

    packages_name = sorted(
        merged_name.items(), key=itemgetter(1), reverse=True)

    for report in problem.reports:
        for backtrace in report.backtraces:
            fid = 0
            for frame in backtrace.frames:
                fid += 1
                frame.nice_order = fid

    bt_hashes = (db.session.query(ReportHash.hash)
                           .join(Report)
                           .join(Problem)
                           .filter(Problem.id == problem_id)
                           .distinct(ReportHash.hash).all())
    bt_hash_qs = "&".join(["bth=" + bth[0] for bth in bt_hashes])

    forward = {"problem": problem,
               "osreleases": osreleases,
               "arches": arches,
               "exes": exes,
               "related_packages_nevr": packages_nevr,
               "related_packages_name": packages_name,
               "bt_hash_qs": bt_hash_qs
               }
    if report_ids:
        bt_diff_form = BacktraceDiffForm()
        bt_diff_form.lhs.choices = [(id, id) for id in report_ids]
        bt_diff_form.rhs.choices = bt_diff_form.lhs.choices
        forward['bt_diff_form'] = bt_diff_form

    return render_template("problems/item.html", **forward)


@problems.route("/bthash/", endpoint="bthash_permalink")
@problems.route("/bthash/<bthash>")
def bthash_forward(bthash=None):
    # single hash
    if bthash is not None:
        db_report = get_report_by_hash(db, bthash)
        if db_report is None:
            raise abort(404)

        if len(db_report.backtraces) < 1:
            return render_template("reports/waitforit.html")

        if db_report.problem is None:
            return render_template("problems/waitforit.html")

        return redirect(url_for("problems.item",
                                problem_id=db_report.problem.id))
    else:
        # multiple hashes as get params
        hashes = request.values.getlist('bth')
        if hashes:
            problems = (db.session.query(Problem)
                                  .join(Report)
                                  .join(ReportHash)
                                  .filter(ReportHash.hash.in_(hashes))
                                  .distinct(Problem.id)
                                  .all())
            if len(problems) == 0:
                abort(404)
            elif len(problems) == 1:
                return redirect(url_for("problems.item",
                                        problem_id=problems[0].id))
            else:
                return render_template("problems/multiple_bthashes.html",
                                       problems=problems)
        else:
            abort(404)
