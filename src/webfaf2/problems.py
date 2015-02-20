import datetime
from collections import defaultdict
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
                           ReportBacktrace,
                           ReportBtFrame,
                           ReportBtTaintFlag,
                           ReportBtThread,
                           ReportExecutable,
                           ReportHash,
                           ReportOpSysRelease,
                           ReportPackage,
                           ReportUnknownPackage,
                           Symbol,
                           SymbolSource)
from pyfaf.queries import (get_history_target, get_report_by_hash,
                           user_is_maintainer)

from flask import (Blueprint, render_template, request,
                   abort, url_for, redirect, jsonify, g)

from sqlalchemy import desc, func, or_

problems = Blueprint("problems", __name__)

from webfaf2_main import db, flask_cache, app
from forms import ProblemFilterForm, BacktraceDiffForm, component_names_to_ids
from utils import cache, Pagination, request_wants_json, metric, metric_tuple


def query_problems(db, hist_table, hist_column,
                   opsysrelease_ids=[], component_ids=[],
                   associate_id=None, arch_ids=[], exclude_taintflag_ids=[],
                   types=[], rank_filter_fn=None, post_process_fn=None,
                   function_names=[], binary_names=[], source_file_names=[],
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
            .distinct(ProblemComponent.problem_id)
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

    if exclude_taintflag_ids:
        etf_sq1 = (
            db.session.query(ReportBtTaintFlag.backtrace_id.label("backtrace_id"))
            .filter(ReportBtTaintFlag.taintflag_id.in_(exclude_taintflag_ids))
            .filter(ReportBacktrace.id == ReportBtTaintFlag.backtrace_id))
        etf_sq2 = (
            db.session.query(ReportBacktrace.report_id.label("report_id"))
            .filter(~etf_sq1.exists())
            .filter(Report.id == ReportBacktrace.report_id))
        etf_sq3 = (
            db.session.query(Report.problem_id.label("problem_id"))
            .filter(etf_sq2.exists())
            .filter(Problem.id == Report.problem_id)
            .subquery())
        final_query = final_query.filter(Problem.id == etf_sq3.c.problem_id)

    if types:
        type_query = (
            db.session.query(Report.problem_id.label("problem_id"))
            .filter(Report.type.in_(types))
            .distinct(Report.problem_id)
            .subquery())

        final_query = final_query.filter(Problem.id == type_query.c.problem_id)

    if function_names or binary_names or source_file_names:
        names_query = (
            db.session.query(Report.problem_id.label("problem_id"))
            .join(ReportBacktrace)
            .join(ReportBtThread)
            .join(ReportBtFrame)
            .join(SymbolSource)
            .filter(ReportBtThread.crashthread == True))

        if function_names:
            names_query = (names_query.join(Symbol)
                           .filter(or_(*([Symbol.name.like(fn) for fn in function_names]+
                                         [Symbol.nice_name.like(fn) for fn in function_names]))))

        if binary_names:
            names_query = names_query.filter(or_(*[SymbolSource.path.like(bn) for bn in binary_names]))

        if source_file_names:
            names_query = names_query.filter(or_(*[SymbolSource.source_path.like(snf)
                                                   for sfn in source_file_names]))

        names_query = names_query.distinct(Report.problem_id).subquery()

        final_query = final_query.filter(Problem.id == names_query.c.problem_id)

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


def get_problems(filter_form, pagination):
    opsysrelease_ids = [
        osr.id for osr in (filter_form.opsysreleases.data or [])]
    component_ids = component_names_to_ids(filter_form.component_names.data)
    if filter_form.associate.data:
        associate_id = filter_form.associate.data.id
    else:
        associate_id = None
    arch_ids = [arch.id for arch in (filter_form.arch.data or [])]
    types = filter_form.type.data or []
    exclude_taintflag_ids = [
        tf.id for tf in (filter_form.exclude_taintflags.data or [])]

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
                       exclude_taintflag_ids=exclude_taintflag_ids,
                       types=types,
                       rank_filter_fn=lambda query: (
                           query.filter(hist_field >= since_date)
                                .filter(hist_field <= to_date)),
                       function_names=filter_form.function_names.data,
                       binary_names=filter_form.binary_names.data,
                       source_file_names=filter_form.source_file_names.data,
                       limit=pagination.limit,
                       offset=pagination.offset)
    return p


def problems_list_table_rows_cache(filter_form, pagination):
    key = ",".join((filter_form.caching_key(),
                    str(pagination.limit),
                    str(pagination.offset)))

    cached = flask_cache.get(key)
    if cached is not None:
        return cached

    p = get_problems(filter_form, pagination)

    cached = (render_template("problems/list_table_rows.html",
                              problems=p), len(p))

    flask_cache.set(key, cached, timeout=60*60)
    return cached


@problems.route("/")
def list():
    pagination = Pagination(request)

    filter_form = ProblemFilterForm(request.args)
    if filter_form.validate():
        if request_wants_json():
            p = get_problems(filter_form, pagination)
        else:
            list_table_rows, problem_count = \
                problems_list_table_rows_cache(filter_form, pagination)

            return render_template("problems/list.html",
                                   list_table_rows=list_table_rows,
                                   problem_count=problem_count,
                                   filter_form=filter_form,
                                   pagination=pagination)
    else:
        p = []

    if request_wants_json():
        return jsonify(dict(problems=p))

    return render_template("problems/list.html",
                           problems=p,
                           problem_count=len(p),
                           filter_form=filter_form,
                           pagination=pagination)


@problems.route("/<int:problem_id>/")
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
           .subquery())

    osreleases = (db.session.query(OpSysRelease, sub.c.cnt)
                            .join(sub)
                            .order_by(desc("cnt"))
                            .all())

    sub = (db.session.query(ReportArch.arch_id,
                            func.sum(ReportArch.count).label("cnt"))
           .join(Report)
           .filter(Report.id.in_(report_ids))
           .group_by(ReportArch.arch_id)
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
           .subquery())
    packages_known = db.session.query(Package, sub.c.cnt).join(sub).all()

    packages_unknown = (db.session.query(ReportUnknownPackage,
                                         ReportUnknownPackage.count)
                                  .join(Report)
                                  .filter(Report.id.in_(report_ids))).all()

    packages = packages_known + packages_unknown

    # creates a package_counts list with this structure:
    # [(package name, count, [(package version, count in the version)])]
    names = defaultdict(lambda: {"count": 0, "versions": defaultdict(int)})
    for (pkg, cnt) in packages:
        names[pkg.name]["name"] = pkg.name
        names[pkg.name]["count"] += cnt
        names[pkg.name]["versions"][pkg.evr()] += cnt

    package_counts = []
    for pkg in sorted(names.values(), key=itemgetter("count"), reverse=True):
        package_counts.append((
            pkg["name"],
            pkg["count"],
            sorted(pkg["versions"].items(), key=itemgetter(1), reverse=True)))

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
               "osreleases": metric(osreleases),
               "arches": metric(arches),
               "exes": metric(exes),
               "package_counts": package_counts,
               "bt_hash_qs": bt_hash_qs
               }

    if request_wants_json():
        return jsonify(forward)

    is_maintainer = app.config["EVERYONE_IS_MAINTAINER"]
    if not is_maintainer and g.user is not None:
        component_ids = set(c.id for c in problem.components)
        if any(user_is_maintainer(db, g.user.username, component_id)
               for component_id in component_ids):
            is_maintainer = True
    forward["is_maintainer"] = is_maintainer

    if report_ids:
        bt_diff_form = BacktraceDiffForm()
        bt_diff_form.lhs.choices = [(id, id) for id in report_ids]
        bt_diff_form.rhs.choices = bt_diff_form.lhs.choices
        forward['bt_diff_form'] = bt_diff_form

    return render_template("problems/item.html", **forward)


@problems.route("/bthash/", endpoint="bthash_permalink")
@problems.route("/bthash/<bthash>/")
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
