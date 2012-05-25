import datetime

from django.template import RequestContext
from django.shortcuts import render_to_response

from sqlalchemy import func
from sqlalchemy.sql.expression import desc

import pyfaf
from pyfaf.storage.problem import Problem, ProblemComponent
from pyfaf.storage.opsys import OpSysComponent, OpSysRelease, Arch, Package
from pyfaf.storage.report import (Report,
                                  ReportArch,
                                  ReportOpSysRelease,
                                  ReportHistoryDaily,
                                  ReportHistoryWeekly,
                                  ReportHistoryMonthly,
                                  ReportExecutable,
                                  ReportPackage)
from pyfaf.hub.common.forms import DurationOsComponentFilterForm
from pyfaf.hub.common.utils import paginate

def query_problems(db, hist_table, hist_column, last_date,
    opsysrelease_ids, component_ids):

    rank_query = (db.session.query(Problem.id.label('id'),
                       func.sum(hist_table.count).label('rank'))
            .join(Report)
            .join(hist_table)
            .filter(hist_column>=last_date)
            .filter(hist_table.opsysrelease_id.in_(opsysrelease_ids))
            .group_by(Problem.id)
            .subquery())

    count_query = (db.session.query(Problem.id.label('id'),
                        func.sum(ReportArch.count).label('count'))
            .join(Report)
            .join(ReportArch)
            .group_by(Problem.id)
            .subquery())

    final_query = (db.session.query(Problem.id,
                        Problem.first_occurence.label('first_appearance'),
                        count_query.c.count,
                        rank_query.c.rank)
            .filter(count_query.c.id==Problem.id)
            .filter(rank_query.c.id==Problem.id)
            .order_by(desc(rank_query.c.rank)))

    if len(component_ids) > 0:
        print component_ids
        final_query = (final_query.join(ProblemComponent)
            .filter(ProblemComponent.component_id.in_(component_ids)))

    problems = final_query.all()
    dummy_rank = 1
    for problem in problems:
        problem.rank = dummy_rank
        problem.component = query_problems_components_csv(db, problem.id)
        dummy_rank += 1

    return problems

def query_problems_components_csv(db, problem_id):
    return (', '.join((problem_component.name for problem_component in
        db.session.query(OpSysComponent.name)
                .join(ProblemComponent)
                .filter(ProblemComponent.problem_id==problem_id)
                .order_by(ProblemComponent.order)
                .all())))

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
    form = DurationOsComponentFilterForm(db, params,
        [('d','7 days'), ('w','14 days'), ('m','4 weeks')])

    table = ReportHistoryDaily
    column = ReportHistoryDaily.day
    last_date = datetime.date.today() - datetime.timedelta(days=7)
    duration = form.get_duration_selection()
    if duration == 'w':
        last_date =  datetime.date.today() - datetime.timedelta(days=14)
    elif duration == 'm':
        table = ReportHistoryWeekly
        column = ReportHistoryWeekly.week
        last_date = get_week_date_before(4)

    ids, names = zip(*form.get_release_selection())

    problems = query_problems(db,
                              table,
                              column,
                              last_date,
                              (osrel_id for lid in ids for osrel_id in lid),
                              form.get_component_selection())

    problems = paginate(problems, request)
    forward = {'problems' : problems,
               'form' : form}

    return render_to_response('problems/hot.html',
                              forward,
                              context_instance=RequestContext(request))

def longterm(request, *args, **kwargs):
    db = pyfaf.storage.getDatabase()
    params = dict(request.REQUEST)
    params.update(kwargs)
    form = DurationOsComponentFilterForm(db, params,
        [('d','6 weeks'), ('w','4 moths'), ('m','9 months')])

    table = ReportHistoryWeekly
    column = ReportHistoryWeekly.week
    last_date = get_week_date_before(6)
    duration = form.get_duration_selection()
    if duration == 'w':
        table = ReportHistoryMonthly
        column = ReportHistoryMonthly.month
        last_date = get_month_date_before(4)
    elif duration == 'm':
        table = ReportHistoryMonthly
        column = ReportHistoryMonthly.month
        last_date = get_month_date_before(9)

    ids, names = zip(*form.get_release_selection())

    problems = query_problems(db,
                              table,
                              column,
                              last_date,
                              (osrel_id for lid in ids for osrel_id in lid),
                              form.get_component_selection())

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

    forward = { 'problem': problem,
                'osreleases': osreleases,
                'arches': arches,
                'exes': exes,
                'packages': packages, }

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
