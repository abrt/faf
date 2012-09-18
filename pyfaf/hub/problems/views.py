import datetime
import functools

from django.http import Http404
from django.template import RequestContext
from django.shortcuts import render_to_response

from sqlalchemy import func
from sqlalchemy.sql.expression import desc, literal

import pyfaf
from pyfaf.storage.problem import Problem, ProblemComponent
from pyfaf.storage.opsys import OpSysComponent, OpSysRelease, Arch, Package
from pyfaf.storage.report import (Report,
                                  ReportArch,
                                  ReportOpSysRelease,
                                  ReportHistoryDaily,
                                  ReportHistoryMonthly,
                                  ReportExecutable,
                                  ReportPackage,
                                  ReportRhbz)
from pyfaf.storage.rhbz import RhbzBug
from pyfaf.hub.common.forms import OsAssociateComponentFilterForm
from pyfaf.hub.common.utils import paginate

def query_problems(db, hist_table, hist_column, opsysrelease_ids, component_ids,
                   rank_filter_fn=None, post_process_fn=None):

    rank_query = (db.session.query(Problem.id.label('id'),
                       func.sum(hist_table.count).label('rank'))
                    .join(Report)
                    .join(hist_table)
                    .filter(hist_table.opsysrelease_id.in_(opsysrelease_ids)))

    if rank_filter_fn:
        rank_query = rank_filter_fn(rank_query)

    rank_query = (rank_query.group_by(Problem.id).subquery())

    # FIXME : replace a virtual value in the state column with a real value
    final_query = (db.session.query(Problem.id,
                        Problem.first_occurence.label('first_appearance'),
                        rank_query.c.rank.label('count'),
                        rank_query.c.rank,
                        literal('PROCESSING').label('state'))
            .filter(rank_query.c.id==Problem.id)
            .order_by(desc(rank_query.c.rank)))

    if len(component_ids) > 0:
        final_query = (final_query.join(ProblemComponent)
            .filter(ProblemComponent.component_id.in_(component_ids)))

    problems = final_query.all()

    if post_process_fn:
        problems = post_process_fn(problems);

    dummy_rank = 1
    for problem in problems:
        problem.rank = dummy_rank
        problem.component = query_problems_components_csv(db, problem.id)
        problem.external_links = query_problems_external_links(db, problem.id)
        dummy_rank += 1

    return problems

def query_problems_components_csv(db, problem_id):
    return (', '.join(set((problem_component.name for problem_component in
        db.session.query(OpSysComponent.name)
                .join(ProblemComponent)
                .filter(ProblemComponent.problem_id==problem_id)
                .order_by(ProblemComponent.order)
                .all()))))

def query_problems_external_links(db, problem_id):
    result = []

    # RHBZ-specific
    # ToDo: do not hardcode bug_url
    bug_url = "https://bugzilla.redhat.com/show_bug.cgi?id="
    bugs = (db.session.query(RhbzBug).join(ReportRhbz)
                                    .join(Report)
                                    .join(Problem)
                                    .filter(Problem.id == problem_id)
                                    .all())
    for bug in bugs:
        result.append(("RHBZ #{0}".format(bug.id),
                       "{0}{1}".format(bug_url, bug.id)))

    # add any other external links here

    return result

def get_week_date_before(nweeks):
    curdate = datetime.date.today()
    return curdate - datetime.timedelta(weeks=nweeks,days=curdate.weekday())

def get_month_date_before(nmonths):
    curdate = datetime.date.today()
    subtract = datetime.timedelta(days=1)
    while nmonths != 0:
        curdate.replace(day=1)
        curdate -= subtract
        nmonths -= 1

    curdate.replace(day=1)
    return curdate

def hot(request, *args, **kwargs):
    db = pyfaf.storage.getDatabase()
    params = dict(request.REQUEST)
    params.update(kwargs)
    form = OsAssociateComponentFilterForm(db, params)


    ids, names = zip(*form.get_release_selection())

    column = ReportHistoryDaily.day
    last_date = datetime.date.today() - datetime.timedelta(days=14)
    problems = query_problems(db,
                              ReportHistoryDaily,
                              column,
                              (osrel_id for lid in ids for osrel_id in lid),
                              form.get_component_selection(),
                              lambda query: query.filter(column>=last_date))

    problems = paginate(problems, request)
    forward = {'problems' : problems,
               'form' : form}

    return render_to_response('problems/hot.html',
                              forward,
                              context_instance=RequestContext(request))

def prioritize_longterm_problems(min_fa, problems):
    '''
    Occurrences holding zero are not stored in the database. In order to work
    out correct average value it is necessary to work out a number of months
    and then divide the total number of occurrences by the worked out sum of
    months. Returned list must be sorted according to priority. The bigger
    average the highest priority.
    '''
    for problem in problems:
        months = (min_fa.month - problem.first_appearance.month) + 1
        if min_fa.year != problem.first_appearance.year:
            months = (min_fa.month
                    + (12 * (min_fa.year - problem.first_appearance.year - 1))
                    + (12 - problem.first_appearance.month))

        if problem.first_appearance.day != 1:
            months -= 1

        problem.rank = problem.rank / float(months)

    return sorted(problems, key=lambda problem: problem.rank, reverse=True);

def longterm(request, *args, **kwargs):
    db = pyfaf.storage.getDatabase()
    params = dict(request.REQUEST)
    params.update(kwargs)
    form = OsAssociateComponentFilterForm(db, params)

    ids, names = zip(*form.get_release_selection())

    # minimal first appearance is the first day of the last month
    min_fa = datetime.date.today()
    min_fa = min_fa.replace(day=1).replace(month=min_fa.month-1);

    problems = query_problems(db,
        ReportHistoryMonthly,
        ReportHistoryMonthly.month,
        (osrel_id for lid in ids for osrel_id in lid),
        form.get_component_selection(),
        lambda query: (
                    # use only Problems that live at least one whole month
                    query.filter(Problem.first_occurence<=min_fa)
                    # do not take into account first incomplete month
                    .filter(Problem.first_occurence<=ReportHistoryMonthly.month)
                    # do not take into account problems that don't have any
                    # occurrence since last month
                    .filter(Problem.id.in_(
                                db.session.query(Problem.id)
                                        .join(Report)
                                        .join(ReportHistoryMonthly)
                                        .filter(Problem.last_occurence>=min_fa)
                                .subquery()))
                    ),
        functools.partial(prioritize_longterm_problems, min_fa));

    problems = paginate(problems, request)
    forward = {'problems' : problems,
               'form' : form}

    return render_to_response('problems/longterm.html',
                              forward,
                              context_instance=RequestContext(request))

def summary(request, **kwargs):
    db = pyfaf.storage.getDatabase()
    problem = db.session.query(Problem).filter(
        Problem.id == kwargs['problem_id']).first()

    if problem is None:
        raise Http404
    report_ids = [report.id for report in problem.reports]

    sub = (db.session.query(ReportOpSysRelease.opsysrelease_id,
                           func.sum(ReportOpSysRelease.count).label('cnt'))
                    .join(Report)
                    .filter(Report.id.in_(report_ids))
                    .group_by(ReportOpSysRelease.opsysrelease_id)
                    .subquery())

    osreleases = db.session.query(OpSysRelease, sub.c.cnt).join(sub).all()

    sub = (db.session.query(ReportArch.arch_id,
                           func.sum(ReportArch.count).label('cnt'))
                    .join(Report)
                    .filter(Report.id.in_(report_ids))
                    .group_by(ReportArch.arch_id)
                    .subquery())

    arches = db.session.query(Arch, sub.c.cnt).join(sub).all()

    exes = (db.session.query(ReportExecutable.path,
                            func.sum(ReportExecutable.count).label('cnt'))
                    .join(Report)
                    .filter(Report.id.in_(report_ids))
                    .group_by(ReportExecutable.path)
                    .all())

    sub = (db.session.query(ReportPackage.installed_package_id,
                           func.sum(ReportPackage.count).label('cnt'))
                    .join(Report)
                    .filter(Report.id.in_(report_ids))
                    .group_by(ReportPackage.installed_package_id)
                    .subquery())
    packages = [(pkg.nevr(), cnt) for (pkg, cnt) in
                db.session.query(Package, sub.c.cnt).join(sub).all()]

    # merge packages with different architectures
    merged = dict()
    for package, count in packages:
        if package in merged:
            merged[package] += count
        else:
            merged[package] = count

    packages = merged

    components = ", ".join(set(c.name for c in problem.components))
    external_links = query_problems_external_links(db, problem.id)

    forward = { 'problem': problem,
                'components': components,
                'osreleases': osreleases,
                'arches': arches,
                'exes': exes,
                'packages': packages,
                'external_links': external_links, }

    return render_to_response('problems/summary.html',
                            forward,
                            context_instance=RequestContext(request))

def backtraces(request):
    return render_to_response('problems/backtraces.html',
                            {},
                            context_instance=RequestContext(request))

def cluster(request):
    return render_to_response('problems/cluster.html',
                            {},
                            context_instance=RequestContext(request))
