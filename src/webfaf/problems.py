import datetime
from collections import defaultdict
from operator import itemgetter
from pyfaf.storage import (Arch,
                           OpSysRelease,
                           OpSysComponent,
                           Package,
                           Problem,
                           ProblemComponent,
                           ProblemReassign,
                           Report,
                           ReportArch,
                           ReportExecutable,
                           ReportHash,
                           ReportOpSysRelease,
                           ReportPackage,
                           ReportUnknownPackage)
from pyfaf.storage.custom_types import to_semver
from pyfaf.queries import (get_history_target, get_report,
                           get_external_faf_instances,
                           get_report_opsysrelease)
from pyfaf.solutionfinders import find_solution

from flask import (Blueprint, render_template, request, abort, url_for,
                   redirect, jsonify, g, stream_with_context, Response, flash)

from sqlalchemy import desc, func
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError

problems = Blueprint("problems", __name__)

from webfaf.webfaf_main import db
from webfaf.forms import (ProblemFilterForm, BacktraceDiffForm,
                          ProblemComponents, component_names_to_ids)
from webfaf.utils import (request_wants_json, metric,
                          is_problem_maintainer, stream_template)


def generate_condition(params_dict, condition_str, param_name, params):
    """Generates part of the SQL search condition for given arguments."""
    tmp_dict = {param_name + str(index): item
                for index, item in enumerate(params)}

    params_dict.update(tmp_dict)
    return condition_str.format(", ".join([":" + o for o in tmp_dict.keys()]))


def query_problems(db, hist_table, hist_column,
                   opsysrelease_ids=[], component_ids=[],
                   associate_id=None, arch_ids=[], exclude_taintflag_ids=[],
                   types=[], since_date=None, to_date=None, post_process_fn=None,
                   function_names=[], binary_names=[], source_file_names=[],
                   since_version=None, since_release=None,
                   to_version=None, to_release=None,
                   probable_fix_osr_ids=[], bug_filter=None,
                   solution=None):
    """Return all data rows of problems dashboard ordered by history counts"""

    select_list = """
SELECT func.id AS id,
       STRING_AGG(DISTINCT(opsyscomponents.name), ', ') AS components,
       MAX(comp.comp_count) AS comp_count,
       MAX(problem_count.count) AS count,
       MAX(func.crashfn) AS crashfn,
       COUNT(DISTINCT(reportmantis.mantisbug_id)) AS mantisbugs_count,
       COUNT(DISTINCT(reportbz.bzbug_id)) AS bzbugs_count,
       MAX(mantisbugs.status) AS mantis_status,
       MAX(bzbugs.status) AS bz_status,
       MAX(fix.pkg_name) AS pkg_name,
       MAX(fix.pkg_version) AS pkg_version,
       MAX(fix.pkg_release) AS pkg_release,
       MAX(fix.name) AS opsys,
       MIN(fix.version) AS opsys_release,
       MAX(untainted.count) AS untainted_count
""".format(hist_table.__tablename__)

    table_list = """
FROM (SELECT problems.id AS id, reportbacktraces.crashfn, COUNT(*) AS func_count
      FROM reportbacktraces
      JOIN reports ON reports.id = reportbacktraces.report_id
      JOIN problems ON problems.id = reports.problem_id
      GROUP BY problems.id, reportbacktraces.crashfn) AS func
JOIN (SELECT func.id, MAX(func.func_count) AS max_count
      FROM (SELECT problems.id, reportbacktraces.crashfn, COUNT(*) AS func_count
            FROM reportbacktraces
            JOIN reports ON reports.id = reportbacktraces.report_id
            JOIN problems ON problems.id = reports.problem_id
            GROUP BY problems.id, reportbacktraces.crashfn) AS func
      GROUP BY func.id) AS common_func
ON func.id = common_func.id AND func.func_count = common_func.max_count
JOIN (SELECT problems.id AS id, COUNT(DISTINCT(opsyscomponents.name)) AS comp_count
      FROM problems
      JOIN problemscomponents ON problems.id = problemscomponents.problem_id
      JOIN opsyscomponents ON problemscomponents.component_id = opsyscomponents.id
      GROUP BY problems.id) AS comp
ON comp.id = func.id
JOIN (SELECT problems.id AS problem_id, SUM({0}.count) AS count
      FROM problems
      JOIN reports ON problems.id = reports.problem_id
      JOIN {0} ON reports.id = {0}.report_id
      WHERE {0}.{1} >= :date_0 AND {0}.{1} <= :date_1
      GROUP BY problems.id) AS problem_count
ON problem_count.problem_id = func.id
JOIN reports ON func.id = reports.problem_id
JOIN {0} ON reports.id = {0}.report_id
JOIN problemscomponents ON func.id = problemscomponents.problem_id
JOIN opsyscomponents ON problemscomponents.component_id = opsyscomponents.id
LEFT JOIN problemopsysreleases ON func.id = problemopsysreleases.problem_id
LEFT JOIN (SELECT problems.id AS id, STRING_AGG(opsys.name, ', ') AS name,
                  STRING_AGG(opsysreleases.version, ', ') As version,
                  STRING_AGG(builds.base_package_name, ', ') AS pkg_name,
                  STRING_AGG(builds.version, ', ') AS pkg_version,
                  STRING_AGG(builds.release, ', ') AS pkg_release
           FROM problems
           JOIN problemopsysreleases ON problems.id = problemopsysreleases.problem_id
           JOIN opsysreleases ON problemopsysreleases.opsysrelease_id = opsysreleases.id
           JOIN opsys ON opsys.id = opsysreleases.opsys_id
           JOIN builds ON problemopsysreleases.probable_fix_build_id = builds.id
           GROUP BY problems.id) AS fix
ON func.id = fix.id
LEFT JOIN (SELECT problem_id AS id, count(reportbacktraces.id)
      FROM reports JOIN problems ON problems.id = reports.problem_id
      JOIN reportbacktraces ON reports.id = reportbacktraces.report_id
      WHERE (problem_id,reportbacktraces.id) NOT IN
          (select backtrace_id, reportbacktraces.id from reportbttaintflags join reportbacktraces ON
          reportbttaintflags.backtrace_id = reportbacktraces.id) group by problem_id ) as untainted
ON func.id = untainted.id
LEFT JOIN reportmantis ON reports.id = reportmantis.report_id
LEFT JOIN mantisbugs ON reportmantis.mantisbug_id = mantisbugs.id
LEFT JOIN reportbz ON reports.id = reportbz.report_id
LEFT JOIN bzbugs ON reportbz.bzbug_id = bzbugs.id
""".format(hist_table.__tablename__, hist_column.key)

    search_condition = []

    params_dict = {"date_0": since_date,
                   "date_1": to_date}

    if solution:
        if not solution.data:
            search_condition.append(
                "(reports.max_certainty < 100 OR reports.max_certainty IS NULL)")

    if opsysrelease_ids:
        search_condition.append(generate_condition(
            params_dict,
            hist_table.__tablename__ + ".opsysrelease_id IN ({0})",
            "opsysrelease_id_",
            opsysrelease_ids))

    if component_ids:
        search_condition.append(generate_condition(
            params_dict,
            "problemscomponents.component_id IN ({0})",
            "component_id_",
            component_ids))

    if associate_id:
        table_list += """
JOIN opsyscomponentsassociates
  ON opsyscomponents.id = opsyscomponentsassociates.opsyscomponent_id
"""

        search_condition.append(
            "opsyscomponentsassociates.associatepeople_id = :associatepeople_id")
        params_dict["associatepeople_id"] = associate_id

    if types:
        search_condition.append(generate_condition(
            params_dict,
            "reports.type IN ({0})",
            "type_",
            types))

    if arch_ids:
        search_condition.append(generate_condition(
            params_dict,
            "reportarchs.arch_id IN ({0})",
            "arch_",
            arch_ids))

        table_list += " JOIN reportarchs ON reportarchs.report_id = reports.id "

    if exclude_taintflag_ids:
        flags_dict = {"flag_id_" + str(index): item
                      for index, item in enumerate(exclude_taintflag_ids)}

        table_list += """
JOIN (SELECT DISTINCT reports.problem_id AS problem_id
      FROM reports JOIN problems ON problems.id = reports.problem_id
      WHERE (EXISTS (SELECT 1
                     FROM reportbacktraces
                     WHERE NOT (EXISTS (SELECT 1
                                        FROM reportbttaintflags
                                        WHERE reportbttaintflags.taintflag_id IN ({0})
                                              AND reportbacktraces.id = reportbttaintflags.backtrace_id))
                                              AND reports.id = reportbacktraces.report_id))
                                              AND problems.id = reports.problem_id) AS flags
ON flags.problem_id = func.id
""".format(", ".join([":" + f for f in flags_dict.keys()]))

        params_dict.update(flags_dict)

    if probable_fix_osr_ids:
        fix_condition = """
(problemopsysreleases.opsysrelease_id IN ({0})
AND problemopsysreleases.probable_fix_build_id IS NOT NULL)
"""
        search_condition.append(generate_condition(
            params_dict,
            fix_condition,
            "osr_",
            probable_fix_osr_ids))

    if bug_filter == "HAS_BUG":
        search_condition.append("""
(reportbz.bzbug_id IS NOT NULL OR reportmantis.mantisbug_id IS NOT NULL)
""")
    elif bug_filter == "NO_BUGS":
        search_condition.append("""
(reportbz.bzbug_id IS NULL AND reportmantis.mantisbug_id IS NULL)
""")
    elif bug_filter == "HAS_OPEN_BUG":
        search_condition.append("""
(bzbugs.status != 'CLOSED' OR mantisbugs.status != 'CLOSED')
""")
    elif bug_filter == "ALL_BUGS_CLOSED":
        search_condition.append("""
(bzbugs.status = 'CLOSED' AND mantisbugs.status = 'CLOSED')
""")
    if function_names:
        func_name_dict = {"func_name_" + str(index): item
                          for index, item in enumerate(function_names)}

        table_list += """
JOIN (SELECT DISTINCT reports.problem_id AS problem_id
      FROM reports
      JOIN reportbacktraces ON reports.id = reportbacktraces.report_id
      JOIN reportbtthreads ON reportbacktraces.id = reportbtthreads.backtrace_id
      JOIN reportbtframes ON reportbtthreads.id = reportbtframes.thread_id
      JOIN symbolsources ON symbolsources.id = reportbtframes.symbolsource_id
      JOIN symbols ON symbols.id = symbolsources.symbol_id
      WHERE reportbtthreads.crashthread = True AND ({0})) AS functions_search
ON functions_search.problem_id = func.id
""".format(" OR ".join(
    ["symbols.name LIKE :{0} OR symbols.nice_name LIKE :{0}".format(name)
     for name in func_name_dict.keys()]))

        params_dict.update(func_name_dict)

    if binary_names or source_file_names:
        names_subquery = """
JOIN (SELECT DISTINCT reports.problem_id AS problem_id
      FROM reports
      JOIN reportbacktraces ON reports.id = reportbacktraces.report_id
      JOIN reportbtthreads ON reportbacktraces.id = reportbtthreads.backtrace_id
      JOIN reportbtframes ON reportbtthreads.id = reportbtframes.thread_id
      JOIN symbolsources ON symbolsources.id = reportbtframes.symbolsource_id
      WHERE reportbtthreads.crashthread = True AND {0} AND {1}) AS binary_search
ON binary_search.problem_id = func.id
"""
    if binary_names and source_file_names:
        binary_name_dict = {"binary_name_" + str(index): item
                            for index, item in enumerate(binary_names)}
        source_file_name_dict = {
            "source_file_name_" +
            str(index): item for index,
            item in enumerate(source_file_names)}

        table_list += names_subquery.format(" OR ".join(
            ["symbolsources.path LIKE :{0} ".format(name)
             for name in binary_name_dict.keys()]),
                                            " OR ".join(
                                                ["symbolsources.source_path LIKE :{0} ".format(name)
                                                 for name in source_file_name_dict.keys()]))

        params_dict.update(binary_name_dict)
        params_dict.update(source_file_name_dict)

    elif binary_names:
        binary_name_dict = {"binary_name_" + str(index): item
                            for index, item in enumerate(binary_names)}

        table_list += names_subquery.format(" OR ".join(
            ["symbolsources.path LIKE :{0} ".format(name)
             for name in binary_name_dict.keys()]), "True")

        params_dict.update(binary_name_dict)

    elif source_file_names:
        source_file_name_dict = {
            "source_file_name_" +
            str(index): item for index,
            item in enumerate(source_file_names)}

        table_list += names_subquery.format(" OR ".join(
            ["symbolsources.source_path LIKE :{0} ".format(name)
             for name in source_file_name_dict.keys()]), "True")

        params_dict.update(source_file_name_dict)

    if since_version or since_release or to_version or to_release:
        params_dict['pkg_type_0'] = 'CRASHED'

        version_subquery = """
JOIN (SELECT DISTINCT reports.problem_id AS problem_id
      FROM reports
      JOIN reportpackages ON reports.id = reportpackages.report_id
      JOIN packages ON packages.id = reportpackages.installed_package_id
      JOIN builds ON builds.id = packages.build_id
      WHERE reportpackages.type = :pkg_type_0 AND ({0})) AS {1}
ON {1}.problem_id = func.id
"""
    if since_version or since_release:
        if since_version and since_release:
            since_condition = """
builds.semver >= :since_ver_0 AND builds.semrel >= :since_rel_0
OR builds.semver >= :since_ver_0
"""
        elif since_version:
            since_condition = "builds.semver >= :since_ver_0"

        elif since_release:
            since_condition = "builds.semrel >= :since_rel_0"

        table_list += version_subquery.format(since_condition, "since_version")
        params_dict.update({
            "since_ver_0": to_semver(since_version),
            "since_rel_0": to_semver(since_release)
        })

    if to_version or to_release:
        if to_version and to_release:
            to_condition = """
builds.semver <= :to_ver_0 AND builds.semrel <= :to_rel_0
OR builds.semver <= :to_ver_0
"""
        elif to_version:
            to_condition = "builds.semver <= :to_ver_0"

        elif to_release:
            to_condition = "builds.semrel <= :to_rel_0"

        table_list += version_subquery.format(to_condition, "to_version")
        params_dict.update({
            "to_ver_0": to_semver(to_version),
            "to_rel_0": to_semver(to_release)
        })
    if search_condition:
        search_condition = "WHERE " + " AND ".join(search_condition)
    else:
        search_condition = ""
    search_condition += " GROUP BY func.id ORDER BY count DESC"
    statement = text(select_list + table_list + search_condition)

    return db.engine.execute(statement, params_dict)


def get_problems(filter_form):
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

    return query_problems(db,
                          hist_table,
                          hist_field,
                          opsysrelease_ids=opsysrelease_ids,
                          component_ids=component_ids,
                          associate_id=associate_id,
                          arch_ids=arch_ids,
                          exclude_taintflag_ids=exclude_taintflag_ids,
                          types=types,
                          since_date=since_date,
                          to_date=to_date,
                          function_names=filter_form.function_names.data,
                          binary_names=filter_form.binary_names.data,
                          source_file_names=filter_form.source_file_names.data,
                          since_version=filter_form.since_version.data,
                          since_release=filter_form.since_release.data,
                          to_version=filter_form.to_version.data,
                          to_release=filter_form.to_release.data,
                          probable_fix_osr_ids=probable_fix_osr_ids,
                          bug_filter=filter_form.bug_filter.data,
                          solution=filter_form.solution)


@problems.route("/")
def dashboard():
    filter_form = ProblemFilterForm(request.args)
    if filter_form.validate():
        p = list(get_problems(filter_form))
    else:
        p = []

    if request_wants_json():
        return jsonify(dict(problems=p))

    return Response(stream_with_context(
        stream_template("problems/list.html",
                        problems=p,
                        filter_form=filter_form)))


@problems.route("/<int:problem_id>/")
@problems.route("/<int:problem_id>/<component_names>")
def item(problem_id, component_names=None):
    components_form = ProblemComponents()

    problem = db.session.query(Problem).filter(
        Problem.id == problem_id).first()

    if problem is None:
        raise abort(404)

    if component_names:
        try:
            (db.session.query(ProblemComponent)
             .filter_by(problem_id=problem_id)
             .delete())

            for index, comp_name in enumerate(component_names.split(',')):
                component = (db.session.query(OpSysComponent)
                             .filter_by(name=comp_name)
                             .first())
                if not component:
                    raise ValueError("Component {} not found.".format(
                        comp_name))

                db.session.add(ProblemComponent(problem_id=problem.id,
                                                component_id=component.id,
                                                order=index + 1))

            reassign = (db.session.query(ProblemReassign)
                        .filter_by(problem_id=problem_id)
                        .first())
            if reassign is None:
                reassign = ProblemReassign(problem_id=problem_id)

            reassign.date = datetime.date.today()
            reassign.username = g.user.username

            db.session.add(reassign)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            flash("Database transaction error.", 'error')
        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'error')

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
               "solutions": solutions,
               "components_form": components_form
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


@problems.route("/bthash/", endpoint="bthash_permalink", methods=["GET", "POST"])
@problems.route("/bthash/<bthash>/", methods=["GET", "POST"])
def bthash_forward(bthash=None):
    # single hash

    # component ids can't be accessed through components_form object because of
    # redirection, it must be passed to the item function as an parameter
    if request.method == 'POST':
        component_names = request.form.get('component_names')
    else:
        component_names = None

    if bthash is not None:
        db_report = get_report(db, bthash)
        if db_report is None:
            raise abort(404)

        if len(db_report.backtraces) < 1:
            return render_template("reports/waitforit.html")

        if db_report.problem is None:
            return render_template("problems/waitforit.html")

        return redirect(url_for("problems.item",
                                problem_id=db_report.problem.id,
                                component_names=component_names))
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
                                        problem_id=problems[0].id,
                                        component_names=component_names))
            else:
                return render_template("problems/multiple_bthashes.html",
                                       problems=problems)
        else:
            abort(404)
