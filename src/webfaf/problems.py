import datetime
from collections import defaultdict
from operator import itemgetter
from pyfaf.storage import (Arch,
                           Build,
                           BuildComponent,
                           BzBug,
                           MantisBug,
                           OpSysComponent,
                           OpSysRelease,
                           OpSysReleaseComponent,
                           OpSysReleaseComponentAssociate,
                           Package,
                           Problem,
                           ProblemComponent,
                           ProblemOpSysRelease,
                           Report,
                           ReportArch,
                           ReportBacktrace,
                           ReportBtFrame,
                           ReportBtTaintFlag,
                           ReportBtThread,
                           ReportBz,
                           ReportExecutable,
                           ReportHash,
                           ReportMantis,
                           ReportOpSysRelease,
                           ReportPackage,
                           ReportUnknownPackage,
                           Symbol,
                           SymbolSource)
from pyfaf.queries import (get_history_target, get_report,
                           get_external_faf_instances,
                           get_report_opsysrelease)
from pyfaf.solutionfinders import find_solution

from flask import (Blueprint, render_template, request,
                   abort, url_for, redirect, jsonify, g)

from sqlalchemy import desc, func, and_, or_

problems = Blueprint("problems", __name__)

from webfaf_main import db, flask_cache, app
from forms import ProblemFilterForm, BacktraceDiffForm, component_names_to_ids
from utils import Pagination, request_wants_json, metric, is_problem_maintainer


def query_problems(db, hist_table, hist_column,
                   opsysrelease_ids=[], component_ids=[],
                   associate_id=None, arch_ids=[], exclude_taintflag_ids=[],
                   types=[], rank_filter_fn=None, post_process_fn=None,
                   function_names=[], binary_names=[], source_file_names=[],
                   since_version=None, since_release=None,
                   to_version=None, to_release=None,
                   probable_fix_osr_ids=[], bug_filter=None,
                   limit=None, offset=None, solution=None):
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

    if solution:
        if not solution.data:
            rank_query = rank_query.filter(or_(Report.max_certainty < 100, Report.max_certainty.is_(None)))

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
            .distinct(Report.problem_id)
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
            names_query = names_query.filter(or_(*[SymbolSource.source_path.like(sfn)
                                                   for sfn in source_file_names]))

        names_query = names_query.distinct(Report.problem_id).subquery()

        final_query = final_query.filter(Problem.id == names_query.c.problem_id)

    if since_version or since_release or to_version or to_release:
        version_query = (
            db.session.query(Report.problem_id.label("problem_id"))
            .join(ReportPackage)
            .join(Package)
            .join(Build)
            .filter(ReportPackage.type == "CRASHED")
            .distinct(Report.problem_id))

        # Make sure only builds of the selected components are considered
        # Requires the find-components action to be run regularly
        if component_ids:
            version_query = (
                version_query
                .join(BuildComponent)
                .filter(BuildComponent.component_id.in_(component_ids))
            )

        if since_version and since_release:
            version_query = version_query.filter(
                or_(
                    and_(Build.semver == since_version,
                         Build.semrel >= since_release),
                    Build.semver > since_version
                )
            )
        elif since_version:
            version_query = version_query.filter(Build.semver >= since_version)
        elif since_release:
            version_query = version_query.filter(Build.semrel >= since_release)

        if to_version and to_release:
            version_query = version_query.filter(
                or_(
                    and_(Build.semver == to_version,
                         Build.semrel <= to_release),
                    Build.semver < to_version
                )
            )
        elif to_version:
            version_query = version_query.filter(Build.semver <= to_version)
        elif to_release:
            version_query = version_query.filter(Build.semrel <= to_release)

        ver_sq = version_query.subquery()
        final_query = final_query.filter(Problem.id == ver_sq.c.problem_id)

    if probable_fix_osr_ids:
        pf_query = (
            db.session.query(ProblemOpSysRelease.problem_id.label("problem_id"))
            .filter(ProblemOpSysRelease.opsysrelease_id.in_(probable_fix_osr_ids))
            .filter(ProblemOpSysRelease.probable_fix_build_id != None)
            .distinct(ProblemOpSysRelease.problem_id)
            .subquery())
        final_query = final_query.filter(Problem.id == pf_query.c.problem_id)

    if bug_filter == "HAS_BUG":
        # Has bugzilla
        bz_query = (
            db.session.query(Report.problem_id.label("problem_id"))
            .join(ReportBz)
            )
        # Has mantis bug
        mantis_query = (
            db.session.query(Report.problem_id.label("problem_id"))
            .join(ReportMantis)
            )
        # Union
        bug_query = (bz_query.union(mantis_query)
                             .distinct(Report.problem_id)
                             .subquery())
        final_query = final_query.filter(Problem.id == bug_query.c.problem_id)
    elif bug_filter == "NO_BUGS":
        # No bugzillas
        bz_query = (
            db.session.query(Report.problem_id.label("problem_id"))
            .outerjoin(ReportBz)
            .group_by(Report.problem_id)
            .having(func.count(ReportBz.report_id) == 0)
            )
        # No Mantis bugs
        mantis_query = (
            db.session.query(Report.problem_id.label("problem_id"))
            .outerjoin(ReportMantis)
            .group_by(Report.problem_id)
            .having(func.count(ReportMantis.report_id) == 0)
            )
        # Intersect
        bug_query = (bz_query.intersect(mantis_query)
                             .distinct(Report.problem_id)
                             .subquery())
        final_query = final_query.filter(Problem.id == bug_query.c.problem_id)
    elif bug_filter == "HAS_OPEN_BUG":
        # Has nonclosed bugzilla
        bz_query = (
            db.session.query(Report.problem_id.label("problem_id"))
            .join(ReportBz)
            .join(BzBug)
            .filter(BzBug.status != "CLOSED")
            )
        # Has nonclosed Mantis bug
        mantis_query = (
            db.session.query(Report.problem_id.label("problem_id"))
            .join(ReportMantis)
            .join(MantisBug)
            .filter(MantisBug.status != "CLOSED")
            )
        # Union
        bug_query = (bz_query.union(mantis_query)
                             .distinct(Report.problem_id)
                             .subquery())
        final_query = final_query.filter(Problem.id == bug_query.c.problem_id)
    elif bug_filter == "ALL_BUGS_CLOSED":
        # Has no bugzilla or no nonclosed bugs
        bz_query = (
            db.session.query(Report.problem_id.label("problem_id"))
            .outerjoin(ReportBz)
            .outerjoin(BzBug)
            .filter(or_(ReportBz.report_id == None, BzBug.status != "CLOSED"))
            .group_by(Report.problem_id)
            .having(func.count(ReportBz.report_id) == 0)
            )
        # Has no Mantis bug or no nonclosed Mantis bugs
        mantis_query = (
            db.session.query(Report.problem_id.label("problem_id"))
            .outerjoin(ReportMantis)
            .outerjoin(MantisBug)
            .filter(or_(ReportMantis.report_id == None, MantisBug.status != "CLOSED"))
            .group_by(Report.problem_id)
            .having(func.count(ReportMantis.report_id) == 0)
            )
        # Intersection gives us also probles with no bugzillas or Mantis bugs
        bug_query_not_closed = bz_query.intersect(mantis_query)

        # We need to intersect this with problems having bugs
        bz_query = (
            db.session.query(Report.problem_id.label("problem_id"))
            .join(ReportBz)
            )
        mantis_query = (
            db.session.query(Report.problem_id.label("problem_id"))
            .join(ReportMantis)
            )

        bug_query = (bz_query.union(mantis_query).intersect(bug_query_not_closed)
                             .distinct(Report.problem_id)
                             .subquery())

        # For some reason the "problem_id" label gets lost in all the
        # unions and intersects so we need to access through items()
        final_query = final_query.filter(Problem.id == bug_query.c.items()[0][1])

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

    probable_fix_osr_ids = [
        osr.id for osr in (filter_form.probable_fix_osrs.data or [])]

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
                       since_version=filter_form.since_version.data,
                       since_release=filter_form.since_release.data,
                       to_version=filter_form.to_version.data,
                       to_release=filter_form.to_release.data,
                       probable_fix_osr_ids=probable_fix_osr_ids,
                       bug_filter=filter_form.bug_filter.data,
                       limit=pagination.limit,
                       offset=pagination.offset,
                       solution=filter_form.solution)
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

    solutions = []
    equal_solution = lambda s: [x for x in solutions if s.cause == x.cause]
    for report in problem.reports:
        if report.max_certainty is not None:
            osr = get_report_opsysrelease(db=db, report_id=report.id)
            solution = find_solution(report, db=db, osr=osr)
            if solution and not equal_solution(solution):
                solutions.append(solution)

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
    # Limit to 10 bt_hashes (otherwise the URL can get too long)
    # Select the 10 hashes uniformly from the entire list to make sure it is a
    # good representation. (Slicing the 10 first could mean the 10 oldest
    # are selected which is not a good representation.)
    k = min(len(bt_hashes), 10)
    a = 0
    d = len(bt_hashes)/float(k)
    bt_hashes_limited = []
    for i in range(k):
        bt_hashes_limited.append("bth=" + bt_hashes[int(a)][0])
        a += d
    bt_hash_qs = "&".join(bt_hashes_limited)

    forward = {"problem": problem,
               "osreleases": metric(osreleases),
               "arches": metric(arches),
               "exes": metric(exes),
               "package_counts": package_counts,
               "bt_hash_qs": bt_hash_qs,
               "solutions": solutions
               }

    if request_wants_json():
        return jsonify(forward)

    is_maintainer = is_problem_maintainer(db, g.user, problem)
    forward["is_maintainer"] = is_maintainer

    forward["extfafs"] = get_external_faf_instances(db)

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
        db_report = get_report(db, bthash)
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
