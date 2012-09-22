import datetime
import functools

from django.http import Http404
from django.template import RequestContext
from django.shortcuts import render_to_response

from sqlalchemy import func
from sqlalchemy.sql.expression import desc

import pyfaf
from pyfaf.storage.problem import Problem, ProblemComponent
from pyfaf.storage.opsys import OpSysRelease, Arch, Package
from pyfaf.storage.report import (Report,
                                  ReportArch,
                                  ReportOpSysRelease,
                                  ReportHistoryDaily,
                                  ReportHistoryMonthly,
                                  ReportExecutable,
                                  ReportPackage)
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

    final_query = (db.session.query(Problem,
                        rank_query.c.rank.label('count'),
                        rank_query.c.rank)
            .filter(rank_query.c.id==Problem.id)
            .order_by(desc(rank_query.c.rank)))

    if len(component_ids) > 0:
        final_query = (final_query.join(ProblemComponent)
            .filter(ProblemComponent.component_id.in_(component_ids)))

    problem_tuples = final_query.all()

    if post_process_fn:
        problems = post_process_fn(problem_tuples);

    for problem, count, rank in problem_tuples:
        problem.count = count
        problem.state = 'Processing'

    return [x[0] for x in problem_tuples]

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

def prioritize_longterm_problems(min_fa, problem_tuples):
    '''
    Occurrences holding zero are not stored in the database. In order to work
    out correct average value it is necessary to work out a number of months
    and then divide the total number of occurrences by the worked out sum of
    months. Returned list must be sorted according to priority. The bigger
    average the highest priority.
    '''
    for problem, count, rank in problem_tuples:
        months = (min_fa.month - problem.first_occurence.month) + 1
        if min_fa.year != problem.first_occurence.year:
            months = (min_fa.month
                    + (12 * (min_fa.year - problem.first_occurence.year - 1))
                    + (12 - problem.first_occurence.month))

        if problem.first_occurence.day != 1:
            months -= 1

        problem.rank = rank / float(months)

    return sorted(problem_tuples, key=lambda (problem, _, __): problem.rank,
        reverse=True);

def longterm(request, *args, **kwargs):
    db = pyfaf.storage.getDatabase()
    params = dict(request.REQUEST)
    params.update(kwargs)
    form = OsAssociateComponentFilterForm(db, params)

    ids, names = zip(*form.get_release_selection())

    # minimal first occurence is the first day of the last month
    min_fo = datetime.date.today()
    min_fo = min_fo.replace(day=1).replace(month=min_fo.month-1);

    problems = query_problems(db,
        ReportHistoryMonthly,
        ReportHistoryMonthly.month,
        (osrel_id for lid in ids for osrel_id in lid),
        form.get_component_selection(),
        lambda query: (
                    # use only Problems that live at least one whole month
                    query.filter(Problem.first_occurence<=min_fo)
                    # do not take into account first incomplete month
                    .filter(Problem.first_occurence<=ReportHistoryMonthly.month)
                    # do not take into account problems that don't have any
                    # occurrence since last month
                    .filter(Problem.id.in_(
                                db.session.query(Problem.id)
                                        .join(Report)
                                        .join(ReportHistoryMonthly)
                                        .filter(Problem.last_occurence>=min_fo)
                                .subquery()))
                    ),
        functools.partial(prioritize_longterm_problems, min_fo));

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

    forward = { 'problem': problem,
                'osreleases': osreleases,
                'arches': arches,
                'exes': exes,
                'packages': packages,
              }

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
