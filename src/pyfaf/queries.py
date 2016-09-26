# Copyright (C) 2013  ABRT Team
# Copyright (C) 2013  Red Hat, Inc.
#
# This file is part of faf.
#
# faf is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# faf is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with faf.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import functools

from pyfaf.storage import (Arch,
                           AssociatePeople,
                           Build,
                           Bugtracker,
                           BzAttachment,
                           BzBug,
                           BzComment,
                           BzUser,
                           ContactEmail,
                           ExternalFafInstance,
                           KernelModule,
                           KernelTaintFlag,
                           MantisBug,
                           OpSys,
                           OpSysComponent,
                           OpSysRelease,
                           OpSysReleaseComponent,
                           OpSysReleaseComponentAssociate,
                           OpSysRepo,
                           Package,
                           PackageDependency,
                           Problem,
                           ProblemComponent,
                           Repo,
                           ProblemOpSysRelease,
                           Report,
                           ReportArch,
                           ReportBacktrace,
                           ReportBtFrame,
                           ReportBtHash,
                           ReportBtThread,
                           ReportBz,
                           ReportContactEmail,
                           ReportExecutable,
                           ReportHash,
                           ReportHistoryDaily,
                           ReportHistoryWeekly,
                           ReportHistoryMonthly,
                           ReportMantis,
                           ReportOpSysRelease,
                           ReportPackage,
                           ReportReason,
                           ReportReleaseDesktop,
                           ReportUnknownPackage,
                           SfPrefilterBacktracePath,
                           SfPrefilterPackageName,
                           SfPrefilterSolution,
                           Symbol,
                           SymbolSource,
                           UnknownOpSys)

from pyfaf.opsys import systems
from sqlalchemy import func, desc

__all__ = ["get_arch_by_name", "get_archs", "get_associate_by_name",
           "get_backtrace_by_hash", "get_backtraces_by_type",
           "get_bugtracker_by_name", "get_bz_attachment", "get_bz_bug",
           "get_bz_comment", "get_bz_user",
           "get_component_by_name", "get_components_by_opsys",
           "get_contact_email", "get_report_contact_email",
           "get_crashed_package_for_report",
           "get_crashed_unknown_package_nevr_for_report",
           "get_debug_files", "get_external_faf_by_baseurl",
           "get_external_faf_by_id", "get_external_faf_by_name",
           "get_external_faf_instances", "get_history_day", "get_history_month",
           "get_history_sum", "get_history_target", "get_history_week",
           "get_sf_prefilter_btpath_by_pattern", "get_sf_prefilter_btpaths",
           "get_sf_prefilter_btpaths_by_solution",
           "get_sf_prefilter_pkgname_by_pattern",
           "get_sf_prefilter_pkgnames", "get_sf_prefilter_pkgnames_by_solution",
           "get_sf_prefilter_sol", "get_sf_prefilter_sols",
           "get_sf_prefilter_sol_by_cause", "get_sf_prefilter_sol_by_id",
           "get_kernelmodule_by_name", "get_opsys_by_name", "get_osrelease",
           "get_package_by_file", "get_packages_by_file",
           "get_package_by_file_build_arch", "get_packages_by_file_builds_arch",
           "get_package_by_name_build_arch", "get_package_by_nevra",
           "get_problems", "get_problem_component", "get_empty_problems",
           "get_problem_opsysrelease", "get_build_by_nevr",
           "get_release_ids", "get_releases", "get_report",
           "get_report_count_by_component", "get_report_release_desktop",
           "get_report_stats_by_component", "get_report_by_id",
           "get_reportarch", "get_reportexe", "get_reportosrelease",
           "get_reportpackage", "get_reportreason", "get_reports_by_type",
           "get_reportbz", "get_reportmantis", "get_reports_for_opsysrelease",
           "get_repos_for_opsys", "get_src_package_by_build",
           "get_ssource_by_bpo", "get_ssources_for_retrace",
           "get_supported_components", "get_symbol_by_name_path",
           "get_symbolsource", "get_taint_flag_by_ureport_name",
           "get_unknown_opsys", "get_unknown_package", "update_frame_ssource",
           "query_hot_problems", "query_longterm_problems",
           "user_is_maintainer"]


def get_arch_by_name(db, arch_name):
    """
    Return pyfaf.storage.Arch object from architecture
    name or None if not found.
    """

    return (db.session.query(Arch)
                      .filter(Arch.name == arch_name)
                      .first())


def get_archs(db):
    """
    Returns the list of all pyfaf.storage.Arch objects.
    """

    return (db.session.query(Arch)
                      .all())


def get_associate_by_name(db, name):
    """
    Returns pyfaf.storage.AssociatePeople object with given
    `name` or None if not found.
    """

    return (db.session.query(AssociatePeople)
                      .filter(AssociatePeople.name == name)
                      .first())


def get_backtrace_by_hash(db, bthash):
    """
    Return pyfaf.storage.ReportBacktrace object from ReportBtHash.hash
    or None if not found.
    """

    return (db.session.query(ReportBacktrace)
                      .join(ReportBtHash)
                      .filter(ReportBtHash.hash == bthash)
                      .first())


def get_backtraces_by_type(db, reporttype, query_all=True):
    """
    Return a list of pyfaf.storage.ReportBacktrace objects
    from textual report type.
    """

    query = (db.session.query(ReportBacktrace)
                       .join(Report)
                       .filter(Report.type == reporttype))

    if not query_all:
        query = query.filter((ReportBacktrace.crashfn == None) |
                             (ReportBacktrace.crashfn == "??"))

    return query


def get_component_by_name(db, component_name, opsys_name):
    """
    Return pyfaf.storage.OpSysComponent from component name
    and operating system name or None if not found.
    """

    return (db.session.query(OpSysComponent)
                      .join(OpSys)
                      .filter(OpSysComponent.name == component_name)
                      .filter(OpSys.name == opsys_name)
                      .first())


def get_component_by_name_release(db, opsysrelease, component_name):
    """
    Return OpSysReleaseComponent instance matching `component_name`
    which also belongs to OpSysRelase instance passed as `opsysrelease`.
    """

    component = (
        db.session.query(OpSysReleaseComponent)
        .join(OpSysComponent)
        .filter(OpSysReleaseComponent.release == opsysrelease)
        .filter(OpSysComponent.name == component_name)
        .first())

    return component


def get_components_by_opsys(db, db_opsys):
    """
    Return a list of pyfaf.storage.OpSysComponent objects
    for a given pyfaf.storage.OpSys.
    """

    return (db.session.query(OpSysComponent)
                      .filter(OpSysComponent.opsys == db_opsys))


def get_contact_email(db, email_address):
    """
    Return ContactEmail for a given email_address
    """
    return (db.session.query(ContactEmail)
                      .filter(ContactEmail.email_address == email_address)
                      .first())


def get_report_contact_email(db, report_id, contact_email_id):
    """
    Return ReportContactEmail for a given report_id and contact_email_id
    """
    return (db.session.query(ReportContactEmail)
                      .filter(ReportContactEmail.contact_email_id == contact_email_id)
                      .filter(ReportContactEmail.report_id == report_id)
                      .first())


def get_debug_files(db, db_package):
    """
    Returns a list of debuginfo files provided by `db_package`.
    """

    deps = (db.session.query(PackageDependency)
                      .filter(PackageDependency.package == db_package)
                      .filter(PackageDependency.type == "PROVIDES")
                      .filter((PackageDependency.name.like("/%%.ko.debug") |
                               (PackageDependency.name.like("/%%/vmlinux"))))
                      .all())

    return [dep.name for dep in deps]


def get_external_faf_by_baseurl(db, baseurl):
    """
    Return pyfaf.storage.ExternalFafInstance with the given
    `baseurl` or None if not found.
    """

    return (db.session.query(ExternalFafInstance)
                      .filter(ExternalFafInstance.baseurl == baseurl)
                      .first())


def get_external_faf_by_id(db, faf_instance_id):
    """
    Return pyfaf.storage.ExternalFafInstance saved under the given
    `faf_instance_id` or None if not found.
    """

    return (db.session.query(ExternalFafInstance)
                      .filter(ExternalFafInstance.id == faf_instance_id)
                      .first())


def get_external_faf_by_name(db, name):
    """
    Return pyfaf.storage.ExternalFafInstance with the given
    `name` or None if not found.
    """

    return (db.session.query(ExternalFafInstance)
                      .filter(ExternalFafInstance.name == name)
                      .first())


def get_external_faf_instances(db):
    """
    Return a list of all pyfaf.storage.ExternalFafInstance objects.
    """

    return (db.session.query(ExternalFafInstance)
                      .all())


def get_history_day(db, db_report, db_osrelease, day):
    """
    Return pyfaf.storage.ReportHistoryDaily object for a given
    report, opsys release and day or None if not found.
    """

    return (db.session.query(ReportHistoryDaily)
                      .filter(ReportHistoryDaily.report == db_report)
                      .filter(ReportHistoryDaily.opsysrelease == db_osrelease)
                      .filter(ReportHistoryDaily.day == day)
                      .first())


def get_history_month(db, db_report, db_osrelease, month):
    """
    Return pyfaf.storage.ReportHistoryMonthly object for a given
    report, opsys release and month or None if not found.
    """

    return (db.session.query(ReportHistoryMonthly)
                      .filter(ReportHistoryMonthly.report == db_report)
                      .filter(ReportHistoryMonthly.opsysrelease == db_osrelease)
                      .filter(ReportHistoryMonthly.month == month)
                      .first())


def get_history_sum(db, opsys_name=None, opsys_version=None,
                    history='daily'):
    """
    Return query summing ReportHistory(Daily|Weekly|Monthly)
    records optinaly filtered by `opsys_name` and `opsys_version`.
    """

    opsysrelease_ids = get_release_ids(db, opsys_name, opsys_version)
    hist_table, hist_field = get_history_target(history)
    hist_sum = db.session.query(func.sum(hist_table.count).label('cnt'))
    if opsysrelease_ids:
        hist_sum = hist_sum.filter(
            hist_table.opsysrelease_id.in_(opsysrelease_ids))

    return hist_sum


def get_history_target(target='daily'):
    """
    Return tuple of `ReportHistory(Daily|Weekly|Monthly)` and
    proper date field `ReportHistory(Daily.day|Weekly.week|Monthly.month)`
    according to `target` parameter which should be one of
    `daily|weekly|monthly` or shortened version `d|w|m`.
    """

    if target == 'd' or target == 'daily':
        return (ReportHistoryDaily, ReportHistoryDaily.day)

    if target == 'w' or target == 'weekly':
        return (ReportHistoryWeekly, ReportHistoryWeekly.week)

    return (ReportHistoryMonthly, ReportHistoryMonthly.month)


def get_history_week(db, db_report, db_osrelease, week):
    """
    Return pyfaf.storage.ReportHistoryWeekly object for a given
    report, opsys release and week or None if not found.
    """

    return (db.session.query(ReportHistoryWeekly)
                      .filter(ReportHistoryWeekly.report == db_report)
                      .filter(ReportHistoryWeekly.opsysrelease == db_osrelease)
                      .filter(ReportHistoryWeekly.week == week)
                      .first())


def get_sf_prefilter_btpath_by_pattern(db, pattern):
    """
    Return a pyfaf.storage.SfPrefilterBacktracePath object with the given
    pattern or None if not found.
    """

    return (db.session.query(SfPrefilterBacktracePath)
                      .filter(SfPrefilterBacktracePath.pattern == pattern)
                      .first())


def get_sf_prefilter_btpaths_by_solution(db, db_solution):
    """
    Return a list of pyfaf.storage.SfPrefilterBacktracePath objects
    with the given pyfaf.storage.SfPrefilterSolution or None if not found.
    """

    return (db.session.query(SfPrefilterBacktracePath)
                      .filter(SfPrefilterBacktracePath.solution == db_solution)
                      .all())


def get_sf_prefilter_btpaths(db, db_opsys=None):
    """
    Return a list of pyfaf.storage.SfPrefilterBacktracePath objects that apply
    to a given operating system.
    """

    return (db.session.query(SfPrefilterBacktracePath)
                      .filter((SfPrefilterBacktracePath.opsys == None) |
                              (SfPrefilterBacktracePath.opsys == db_opsys))
                      .all())


def get_sf_prefilter_pkgname_by_pattern(db, pattern):
    """
    Return a pyfaf.storage.SfPrefilterPackageName object with the given
    pattern or None if not found.
    """

    return (db.session.query(SfPrefilterPackageName)
                      .filter(SfPrefilterPackageName.pattern == pattern)
                      .first())


def get_sf_prefilter_pkgnames_by_solution(db, db_solution):
    """
    Return a list of pyfaf.storage.SfPrefilterPackageName objects
    with the given pyfaf.storage.SfPrefilterSolution or None if not found.
    """

    return (db.session.query(SfPrefilterPackageName)
                      .filter(SfPrefilterPackageName.solution == db_solution)
                      .all())


def get_sf_prefilter_pkgnames(db, db_opsys=None):
    """
    Return a list of pyfaf.storage.SfPrefilterBacktracePath objects that apply
    to a given operating system.
    """

    return (db.session.query(SfPrefilterPackageName)
                      .filter((SfPrefilterPackageName.opsys == None) |
                              (SfPrefilterPackageName.opsys == db_opsys))
                      .all())


def get_sf_prefilter_sol(db, key):
    """
    Return pyfaf.storage.SfPrefilterSolution object for a given key
    (numeric ID or textual cause) or None if not found.
    """

    try:
        sf_prefilter_sol_id = int(key)
        return get_sf_prefilter_sol_by_id(db, sf_prefilter_sol_id)
    except (ValueError, TypeError):
        return get_sf_prefilter_sol_by_cause(db, key)


def get_sf_prefilter_sols(db):
    """
    Return list of all pyfaf.storage.SfPrefilterSolution objects.
    """

    return (db.session.query(SfPrefilterSolution)
                      .all())


def get_sf_prefilter_sol_by_cause(db, cause):
    """
    Return pyfaf.storage.SfPrefilterSolution object for a given
    textual cause or None if not found.
    """

    return (db.session.query(SfPrefilterSolution)
                      .filter(SfPrefilterSolution.cause == cause)
                      .first())


def get_sf_prefilter_sol_by_id(db, solution_id):
    """
    Return pyfaf.storage.SfPrefilterSolution object for a given
    ID or None if not found.
    """

    return (db.session.query(SfPrefilterSolution)
                      .filter(SfPrefilterSolution.id == solution_id)
                      .first())


def get_kernelmodule_by_name(db, module_name):
    """
    Return pyfaf.storage.KernelModule from module name or None if not found.
    """

    return (db.session.query(KernelModule)
                      .filter(KernelModule.name == module_name)
                      .first())


def get_opsys_by_name(db, name):
    """
    Return pyfaf.storage.OpSys from operating system
    name or None if not found.
    """

    return (db.session.query(OpSys)
                      .filter(OpSys.name == name)
                      .first())


def get_osrelease(db, name, version):
    """
    Return pyfaf.storage.OpSysRelease from operating system
    name and version or None if not found.
    """

    return (db.session.query(OpSysRelease)
                      .join(OpSys)
                      .filter(OpSys.name == name)
                      .filter(OpSysRelease.version == version)
                      .first())


def get_package_by_file(db, filename):
    """
    Return pyfaf.storage.Package object providing the file named `filename`
    or None if not found.
    """

    return (db.session.query(Package)
                      .join(PackageDependency)
                      .filter(PackageDependency.name == filename)
                      .filter(PackageDependency.type == "PROVIDES")
                      .first())


def get_packages_by_file(db, filename):
    """
    Return a list of pyfaf.storage.Package objects
    providing the file named `filename`.
    """

    return (db.session.query(Package)
                      .join(PackageDependency)
                      .filter(PackageDependency.name == filename)
                      .filter(PackageDependency.type == "PROVIDES")
                      .all())


def get_package_by_file_build_arch(db, filename, db_build, db_arch):
    """
    Return pyfaf.storage.Package object providing the file named `filename`,
    belonging to `db_build` and of given architecture, or None if not found.
    """

    return (db.session.query(Package)
                      .join(PackageDependency)
                      .filter(Package.build == db_build)
                      .filter(Package.arch == db_arch)
                      .filter(PackageDependency.name == filename)
                      .filter(PackageDependency.type == "PROVIDES")
                      .first())


def get_packages_by_file_builds_arch(db, filename, db_build_ids,
                                     db_arch, abspath=True):
    """
    Return a list of pyfaf.storage.Package object providing the file named
    `filename`, belonging to any of `db_build_ids` and of given architecture.
    If `abspath` is True, the `filename` must match the RPM provides entry.
    If `abspath` is False, the `filename` must be a suffix of the RPM entry.
    """

    query_base = (db.session.query(Package)
                            .join(PackageDependency)
                            .filter(Package.build_id.in_(db_build_ids))
                            .filter(Package.arch == db_arch)
                            .filter(PackageDependency.type == "PROVIDES"))

    if abspath:
        return query_base.filter(PackageDependency.name == filename).all()

    wildcard = "%/{0}".format(filename)
    return query_base.filter(PackageDependency.name.like(wildcard)).all()


def get_package_by_name_build_arch(db, name, db_build, db_arch):
    """
    Return pyfaf.storage.Package object named `name`,
    belonging to `db_build` and of given architecture, or None if not found.
    """

    return (db.session.query(Package)
                      .filter(Package.build == db_build)
                      .filter(Package.arch == db_arch)
                      .filter(Package.name == name)
                      .first())


def get_package_by_nevra(db, name, epoch, version, release, arch):
    """
    Return pyfaf.storage.Package object from NEVRA or None if not found.
    """

    return (db.session.query(Package)
                      .join(Build)
                      .join(Arch)
                      .filter(Package.name == name)
                      .filter(Build.epoch == epoch)
                      .filter(Build.version == version)
                      .filter(Build.release == release)
                      .filter(Arch.name == arch)
                      .first())


def get_build_by_nevr(db, name, epoch, version, release):
    """
    Return pyfaf.storage.Build object from NEVR or None if not found.
    """

    return (db.session.query(Build)
                      .filter(Build.base_package_name == name)
                      .filter(Build.epoch == epoch)
                      .filter(Build.version == version)
                      .filter(Build.release == release)
                      .first())


def get_problems(db):
    """
    Return a list of all pyfaf.storage.Problem in the storage.
    """

    return (db.session.query(Problem)
                      .all())


def get_empty_problems(db):
    """
    Return a list of pyfaf.storage.Problem that have no reports.
    """
    return (db.session.query(Problem)
                      .outerjoin(Report)
                      .group_by(Problem)
                      .having(func.count(Report.id) == 0)
                      .all())


def query_problems(db, hist_table, hist_column, opsysrelease_ids, component_ids,
                   rank_filter_fn=None, post_process_fn=None):
    """
    Return problems ordered by history counts
    """

    rank_query = (db.session.query(Problem.id.label('id'),
                                   func.sum(hist_table.count).label('rank'))
                  .join(Report)
                  .join(hist_table)
                  .filter(hist_table.opsysrelease_id.in_(opsysrelease_ids)))

    if rank_filter_fn:
        rank_query = rank_filter_fn(rank_query)

    rank_query = (rank_query.group_by(Problem.id).subquery())

    final_query = (
        db.session.query(Problem,
                         rank_query.c.rank.label('count'),
                         rank_query.c.rank)
        .filter(rank_query.c.id == Problem.id)
        .order_by(desc(rank_query.c.rank)))

    if component_ids is not None:
        final_query = (
            final_query.join(ProblemComponent)
            .filter(ProblemComponent.component_id.in_(component_ids)))

    problem_tuples = final_query.all()

    if post_process_fn:
        problem_tuples = post_process_fn(problem_tuples)

    for problem, count, rank in problem_tuples:
        problem.count = count

    return [x[0] for x in problem_tuples]


def query_hot_problems(db, opsysrelease_ids,
                       component_ids=None, last_date=None,
                       history="daily"):
    """
    Return top problems since `last_date` (2 weeks ago by default)
    """

    if last_date is None:
        last_date = datetime.date.today() - datetime.timedelta(days=14)

    hist_table, hist_field = get_history_target(history)

    return query_problems(db,
                          hist_table,
                          hist_field,
                          opsysrelease_ids,
                          component_ids,
                          lambda query: query.filter(hist_field >= last_date))


def prioritize_longterm_problems(min_fa, problem_tuples):
    """
    Occurrences holding zero are not stored in the database. In order to work
    out correct average value it is necessary to work out a number of months
    and then divide the total number of occurrences by the worked out sum of
    months. Returned list must be sorted according to priority. The bigger
    average the highest priority.
    """

    for problem, count, rank in problem_tuples:
        months = (min_fa.month - problem.first_occurrence.month) + 1
        if min_fa.year != problem.first_occurrence.year:
            months = (min_fa.month
                      +
                      (12 * (min_fa.year - problem.first_occurrence.year - 1))
                      + (13 - problem.first_occurrence.month))

        if problem.first_occurrence.day != 1:
            months -= 1

        problem.rank = rank / float(months)

    return sorted(problem_tuples, key=lambda (problem, _, __): problem.rank,
                  reverse=True)


def query_longterm_problems(db, opsysrelease_ids, component_ids=None,
                            history="monthly"):
    """
    Return top long-term problems
    """

    # minimal first occurrence is the first day of the last month
    min_fo = datetime.date.today().replace(day=1) - datetime.timedelta(days=1)
    min_fo = min_fo.replace(day=1)

    hist_table, hist_field = get_history_target(history)

    return query_problems(
        db,
        hist_table,
        hist_field,
        opsysrelease_ids,
        component_ids,
        lambda query: (
            # use only Problems that live at least one whole month
            query.filter(Problem.first_occurrence <= min_fo)
            # do not take into account first incomplete month
            .filter(Problem.first_occurrence <= hist_field)
            # do not take into account problems that don't have any
            # occurrence since last month
            .filter(Problem.id.in_(
                db.session.query(Problem.id)
                .join(Report)
                .join(hist_table)
                .filter(Problem.last_occurrence >= min_fo)
                .subquery()))
        ),
        functools.partial(prioritize_longterm_problems, min_fo))


def get_problem_component(db, db_problem, db_component):
    """
    Return pyfaf.storage.ProblemComponent object from problem and component
    or None if not found.
    """

    return (db.session.query(ProblemComponent)
                      .filter(ProblemComponent.problem == db_problem)
                      .filter(ProblemComponent.component == db_component)
                      .first())


def get_release_ids(db, opsys_name=None, opsys_version=None):
    """
    Return list of `OpSysRelease` ids optionaly filtered
    by `opsys_name` and `opsys_version`.
    """

    return [opsysrelease.id for opsysrelease in
            get_releases(db, opsys_name, opsys_version).all()]


def get_releases(db, opsys_name=None, opsys_version=None):
    """
    Return query of `OpSysRelease` records optionaly filtered
    by `opsys_name` and `opsys_version`.
    """

    opsysquery = (
        db.session.query(OpSysRelease)
        .join(OpSys))

    if opsys_name:
        opsysquery = opsysquery.filter(OpSys.name == opsys_name)

    if opsys_version:
        opsysquery = opsysquery.filter(OpSysRelease.version == opsys_version)

    return opsysquery


def get_report_by_id(db, report_id):
    """
    Return pyfaf.storage.Report object by report_id
    or None if not found.
    """

    return (db.session.query(Report)
                      .filter(Report.id == report_id)
                      .first())


def get_report(db, report_hash, os_name=None, os_version=None, os_arch=None):
    '''
    Return pyfaf.storage.Report object or None if not found
    This method takes optionally parameters for searching
    Reports by os parameters
    '''

    result = None

    db_query = (db.session.query(Report)
                .join(ReportHash)
                .filter(ReportHash.hash == report_hash))

    if os_name:
        osplugin = systems[os_name]

        db_query = (db_query
                    .join(ReportOpSysRelease)
                    .join(OpSysRelease, ReportOpSysRelease.opsysrelease_id == OpSysRelease.id)
                    .join(OpSys, OpSysRelease.opsys_id == OpSys.id)
                    .filter(OpSys.name == osplugin.nice_name)
                    .filter(ReportOpSysRelease.report_id == Report.id))

    if os_version:
        if not os_name:
            db_query = (db_query.join(ReportOpSysRelease))

        db_query = (db_query
                    .filter(OpSysRelease.version == os_version))

    if os_arch:
        db_query = (db_query
                    .join(ReportArch)
                    .join(Arch, ReportArch.arch_id == Arch.id)
                    .filter(Arch.name == os_arch))

    return db_query.first()


def get_report_count_by_component(db, opsys_name=None, opsys_version=None,
                                  history='daily'):
    """
    Return query for `OpSysComponent` and number of reports this
    component received.

    Optionally filtered by `opsys_name` and `opsys_version`.
    """

    opsysrelease_ids = get_release_ids(db, opsys_name, opsys_version)
    hist_table, hist_field = get_history_target(history)

    comps = (
        db.session.query(OpSysComponent,
                         func.sum(hist_table.count).label('cnt'))
        .join(Report)
        .join(hist_table)
        .group_by(OpSysComponent)
        .order_by(desc('cnt')))

    if opsysrelease_ids:
        comps = comps.filter(hist_table.opsysrelease_id.in_(opsysrelease_ids))

    return comps


def get_report_release_desktop(db, db_report, db_release, desktop):
    """
    Return `pyfaf.storage.ReportReleaseDesktop` object for given
    report, release and desktop or None if not found.
    """

    return (db.session.query(ReportReleaseDesktop)
                      .filter(ReportReleaseDesktop.report == db_report)
                      .filter(ReportReleaseDesktop.release == db_release)
                      .filter(ReportReleaseDesktop.desktop == desktop)
                      .first())


def get_report_stats_by_component(db, component, opsys_name=None,
                                  opsys_version=None, history='daily'):
    """
    Return query with reports for `component` along with
    summed counts from `history` table (one of daily/weekly/monthly).

    Optionally filtered by `opsys_name` and `opsys_version`.
    """

    hist_table, hist_field = get_history_target(history)
    opsysrelease_ids = get_release_ids(db, opsys_name, opsys_version)

    stats = (db.session.query(Report,
                              func.sum(hist_table.count).label('cnt'))
             .join(hist_table)
             .join(OpSysComponent)
             .filter(OpSysComponent.id == component.id)
             .group_by(Report)
             .order_by(desc('cnt')))

    if opsysrelease_ids:
        stats = stats.filter(hist_table.opsysrelease_id.in_(opsysrelease_ids))

    return stats


def get_reportarch(db, report, arch):
    """
    Return pyfaf.storage.ReportArch object from pyfaf.storage.Report
    and pyfaf.storage.Arch or None if not found.
    """

    return (db.session.query(ReportArch)
                      .filter(ReportArch.report == report)
                      .filter(ReportArch.arch == arch)
                      .first())


def get_reportexe(db, report, executable):
    """
    Return pyfaf.storage.ReportExecutable object from pyfaf.storage.Report
    and the absolute path of executable or None if not found.
    """

    return (db.session.query(ReportExecutable)
                      .filter(ReportExecutable.report == report)
                      .filter(ReportExecutable.path == executable)
                      .first())


def get_reportosrelease(db, report, osrelease):
    """
    Return pyfaf.storage.ReportOpSysRelease object from pyfaf.storage.Report
    and pyfaf.storage.OpSysRelease or None if not found.
    """

    return (db.session.query(ReportOpSysRelease)
                      .filter(ReportOpSysRelease.report == report)
                      .filter(ReportOpSysRelease.opsysrelease == osrelease)
                      .first())


def get_reportpackage(db, report, package):
    """
    Return pyfaf.storage.ReportPackage object from pyfaf.storage.Report
    and pyfaf.storage.Package or None if not found.
    """

    return (db.session.query(ReportPackage)
                      .filter(ReportPackage.report == report)
                      .filter(ReportPackage.installed_package == package)
                      .first())


def get_reportreason(db, report, reason):
    """
    Return pyfaf.storage.ReportReason object from pyfaf.storage.Report
    and the textual reason or None if not found.
    """

    return (db.session.query(ReportReason)
                      .filter(ReportReason.report == report)
                      .filter(ReportReason.reason == reason)
                      .first())


def get_reports_by_type(db, report_type, min_count=0):
    """
    Return pyfaf.storage.Report object list from
    the textual type or an empty list if not found.
    """
    q = (db.session.query(Report)
                   .filter(Report.type == report_type))
    if min_count > 0:
        q = q.filter(Report.count >= min_count)
    return q.all()


def remove_problem_from_low_count_reports_by_type(db, report_type, min_count):
    """
    Set problem_id = NULL for reports of given `report_type` where count is
    less than `min_count`.
    """

    return (db.session.query(Report)
                      .filter(Report.type == report_type)
                      .filter(Report.count < min_count)
                      .update({Report.problem_id: None},
                              synchronize_session=False))


def get_reportbz(db, report_id, opsysrelease_id=None):
    """
    Return pyfaf.storage.ReportBz objects of given `report_id`.
    Optionally filter by `opsysrelease_id` of the BzBug.
    """

    query = (db.session.query(ReportBz)
                       .filter(ReportBz.report_id == report_id))
    if opsysrelease_id:
        query = (query.join(BzBug)
                      .filter(BzBug.opsysrelease_id == opsysrelease_id))

    return query


def get_reportbz_by_major_version(db, report_id, major_version):
    """
    Return pyfaf.storage.ReportBz objects of given `report_id`.
    Optionally filter by `opsysrelease_id` of the BzBug.
    """

    query = (db.session.query(ReportBz)
             .join(BzBug)
             .join(OpSysRelease)
             .filter(ReportBz.report_id == report_id)
             .filter(OpSysRelease.version.like(str(major_version) + ".%")))

    return query


def get_reportmantis(db, report_id, opsysrelease_id=None):
    """
    Return pyfaf.storage.ReportMantis objects of given `report_id`.
    Optionally filter by `opsysrelease_id` of the MantisBug.
    """
    query = (db.session.query(ReportMantis)
                       .filter(ReportMantis.report_id == report_id))
    if opsysrelease_id:
        query = (query.join(MantisBug)
                      .filter(MantisBug.opsysrelease_id == opsysrelease_id))

    return query


def get_repos_for_opsys(db, opsys_id):
    """
    Return Repos assigned to given `opsys_id`.
    """
    return (db.session.query(Repo)
                      .join(OpSysRepo)
                      .filter(OpSysRepo.opsys_id == opsys_id)
                      .all())


def get_src_package_by_build(db, db_build):
    """
    Return pyfaf.storage.Package object, which is the source package
    for given pyfaf.storage.Build or None if not found.
    """

    return (db.session.query(Package)
                      .join(Arch)
                      .filter(Package.build == db_build)
                      .filter(Arch.name == "src")
                      .first())


def get_ssource_by_bpo(db, build_id, path, offset):
    """
    Return pyfaf.storage.SymbolSource object from build id,
    path and offset or None if not found.
    """

    return (db.session.query(SymbolSource)
                      .filter(SymbolSource.build_id == build_id)
                      .filter(SymbolSource.path == path)
                      .filter(SymbolSource.offset == offset)
                      .first())


def get_ssources_for_retrace(db, problemtype):
    """
    Return a list of pyfaf.storage.SymbolSource objects of given
    problem type that need retracing.
    """

    return (db.session.query(SymbolSource)
                      .join(ReportBtFrame)
                      .join(ReportBtThread)
                      .join(ReportBacktrace)
                      .join(Report)
                      .filter(Report.type == problemtype)
                      .filter((SymbolSource.symbol == None) |
                              (SymbolSource.source_path == None) |
                              (SymbolSource.line_number == None))
                      .all())


def get_supported_components(db):
    """
    Return a list of pyfaf.storage.OpSysReleaseComponent that
    are mapped to an active release (not end-of-life).
    """

    return (db.session.query(OpSysReleaseComponent)
                      .join(OpSysRelease)
                      .filter(OpSysRelease.status != 'EOL')
                      .all())


def get_symbol_by_name_path(db, name, path):
    """
    Return pyfaf.storage.Symbol object from symbol name
    and normalized path or None if not found.
    """

    return (db.session.query(Symbol)
                      .filter(Symbol.name == name)
                      .filter(Symbol.normalized_path == path)
                      .first())


def get_symbolsource(db, symbol, filename, offset):
    """
    Return pyfaf.storage.SymbolSource object from pyfaf.storage.Symbol,
    file name and offset or None if not found.
    """

    return (db.session.query(SymbolSource)
                      .filter(SymbolSource.symbol == symbol)
                      .filter(SymbolSource.path == filename)
                      .filter(SymbolSource.offset == offset)
                      .first())


def get_taint_flag_by_ureport_name(db, ureport_name):
    """
    Return pyfaf.storage.KernelTaintFlag from flag name or None if not found.
    """

    return (db.session.query(KernelTaintFlag)
                      .filter(KernelTaintFlag.ureport_name == ureport_name)
                      .first())


def get_unknown_opsys(db, name, version):
    """
    Return pyfaf.storage.UnknownOpSys object from name and version
    or None if not found.
    """

    return (db.session.query(UnknownOpSys)
                      .filter(UnknownOpSys.name == name)
                      .filter(UnknownOpSys.version == version)
                      .first())


def get_unknown_package(db, db_report, role, name,
                        epoch, version, release, arch):
    """
    Return pyfaf.storage.ReportUnknownPackage object from pyfaf.storage.Report,
    package role and NEVRA or None if not found.
    """

    db_arch = get_arch_by_name(db, arch)
    return (db.session.query(ReportUnknownPackage)
                      .filter(ReportUnknownPackage.report == db_report)
                      .filter(ReportUnknownPackage.type == role)
                      .filter(ReportUnknownPackage.name == name)
                      .filter(ReportUnknownPackage.epoch == epoch)
                      .filter(ReportUnknownPackage.version == version)
                      .filter(ReportUnknownPackage.release == release)
                      .filter(ReportUnknownPackage.arch == db_arch)
                      .first())


def get_packages_and_their_reports_unknown_packages(db):
    """
    Return tuples (Package, ReportUnknownPackage) that are joined by package name and
    NEVRA through Build of the Package.

    """

    return (db.session.query(Package, ReportUnknownPackage)
                      .join(Build, Build.id == Package.build_id)
                      .filter(Package.name == ReportUnknownPackage.name)
                      .filter(Package.arch_id == ReportUnknownPackage.arch_id)
                      .filter(Build.epoch == ReportUnknownPackage.epoch)
                      .filter(Build.version == ReportUnknownPackage.version)
                      .filter(Build.release == ReportUnknownPackage.release))


def update_frame_ssource(db, db_ssrc_from, db_ssrc_to):
    """
    Replaces pyfaf.storage.SymbolSource `db_ssrc_from` by `db_ssrc_to` in
    all affected frames.
    """

    db_frames = (db.session.query(ReportBtFrame)
                           .filter(ReportBtFrame.symbolsource == db_ssrc_from))

    for db_frame in db_frames:
        db_frame.symbolsource = db_ssrc_to

    db.session.flush()


def get_bugtracker_by_name(db, name):
    return (db.session.query(Bugtracker)
            .filter(Bugtracker.name == name)
            .first())


def get_bz_bug(db, bug_id):
    """
    Return BzBug instance if there is a bug in the database
    with `bug_id` id.
    """

    return (db.session.query(BzBug)
            .filter(BzBug.id == bug_id)
            .first())


def get_bz_comment(db, comment_id):
    """
    Return BzComment instance if there is a comment in the database
    with `comment_id` id.
    """

    return (db.session.query(BzComment)
            .filter(BzComment.id == comment_id)
            .first())


def get_bz_user(db, user_email):
    """
    Return BzUser instance if there is a user in the database
    with `user_id` id.
    """

    return (db.session.query(BzUser)
            .filter(BzUser.email == user_email)
            .first())


def get_bz_attachment(db, attachment_id):
    """
    Return BzAttachment instance if there is an attachment in
    the database with `attachment_id` id.
    """

    return (db.session.query(BzAttachment)
            .filter(BzAttachment.id == attachment_id)
            .first())


def get_crashed_package_for_report(db, report_id):
    """
    Return Packages that CRASHED in a given report.
    """
    return (db.session.query(Package)
                      .join(ReportPackage.installed_package)
                      .filter(ReportPackage.installed_package_id == Package.id)
                      .filter(ReportPackage.report_id == report_id)
                      .filter(ReportPackage.type == "CRASHED")
                      .all())


def get_crashed_unknown_package_nevr_for_report(db, report_id):
    """
    Return (n,e,v,r) tuples for and unknown packages that CRASHED in a given
    report.
    """
    return (db.session.query(ReportUnknownPackage.name,
                             ReportUnknownPackage.epoch,
                             ReportUnknownPackage.version,
                             ReportUnknownPackage.release)
            .filter(ReportUnknownPackage.report_id == report_id)
            .filter(ReportUnknownPackage.type == "CRASHED")
            .all())


def get_problem_opsysrelease(db, problem_id, opsysrelease_id):
    return (db.session.query(ProblemOpSysRelease)
                      .filter(ProblemOpSysRelease.problem_id == problem_id)
                      .filter(ProblemOpSysRelease.opsysrelease_id == opsysrelease_id)
                      .first())


def get_reports_for_opsysrelease(db, problem_id, opsysrelease_id):
    return (db.session.query(Report)
                      .join(ReportOpSysRelease)
                      .filter(ReportOpSysRelease.opsysrelease_id == opsysrelease_id)
                      .filter(Report.problem_id == problem_id).all())


def user_is_maintainer(db, username, component_id):
    return (db.session.query(AssociatePeople)
                      .join(OpSysReleaseComponentAssociate)
                      .join(OpSysReleaseComponent)
                      .filter(AssociatePeople.name == username)
                      .filter(OpSysReleaseComponent.components_id == component_id)
                      .filter(OpSysReleaseComponentAssociate.permission == "commit")
                      .count()) > 0


def get_mantis_bug(db, external_id, tracker_id):
    """
    Return MantisBug instance if there is a bug in the database
    with `(external_id, tracker_id)`.
    """

    return (db.session.query(MantisBug)
            .filter(MantisBug.external_id == external_id)
            .filter(MantisBug.tracker_id == tracker_id)
            .first())


def get_report_opsysrelease(db, report_id):
    return (db.session.query(OpSysRelease)
            .join(ReportOpSysRelease)
            .filter(ReportOpSysRelease.report_id == report_id)
            .first())
