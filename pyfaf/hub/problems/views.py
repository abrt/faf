import datetime
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.conf import settings
from sqlalchemy import func
from sqlalchemy.sql.expression import desc
import pyfaf
from pyfaf.storage import *
from ..common.forms import DurationOsComponentFilterForm

def query_problems(db, hist_table, hist_column, last_date, opsysrelease_id, component_id):
    rank_query = db.session.query(Problem.id.label("id"),\
                            func.sum(hist_table.count).label("rank"))\
            .join(Report)\
            .join(hist_table)\
            .filter(hist_column>=last_date)\
            .group_by(Problem.id)\
            .subquery()

    count_query = db.session.query(Problem.id.label("id"),\
                            func.sum(ReportArch.count).label("count"))\
            .join(Report)\
            .join(ReportArch)\
            .group_by(Problem.id)\
            .subquery()

    final_query = db.session.query(Problem.id, Problem.first_occurence.label("first_appearance"), count_query.c.count, rank_query.c.rank)\
            .join(Report)\
            .join(OpSysComponent)\
            .join(OpSys)\
            .join(ReportOpSysRelease)\
            .filter(count_query.c.id==Problem.id)\
            .filter(rank_query.c.id==Problem.id)\
            .filter(ReportOpSysRelease.opsysrelease_id==opsysrelease_id)\
            .order_by(desc(rank_query.c.rank))

    if component_id >= 0:
        final_query = final_query.filter(OpSysComponent.id==component_id)

    return final_query.all()

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

    

def hot(request):
    db = pyfaf.storage.getDatabase()
    filter_form = DurationOsComponentFilterForm(db, request.REQUEST, [('d','7 days'),('w','14 days'),('m','4 weeks')])

    table, column, last_date = ReportHistoryDaily, ReportHistoryDaily.day, datetime.date.today() - datetime.timedelta(days=7)
    if filter_form.fields['duration'].initial == 'w':
        last_date =  datetime.date.today() - datetime.timedelta(days=14)
    elif filter_form.fields['duration'].initial == 'm':
        table, column, last_date = ReportHistoryWeekly, ReportHistoryWeekly.week, get_week_date_before(4)

    problems = query_problems(db, table, column, last_date,\
                                filter_form.fields['os_release'].initial, filter_form.fields['component'].initial)

    forward = {"problems" : problems,
               "form" : filter_form}

    return render_to_response('problems/hot.html',\
                              forward,\
                              context_instance=RequestContext(request))

def longterm(request):
    db = pyfaf.storage.getDatabase()
    filter_form = DurationOsComponentFilterForm(db, request.REQUEST, [('d','6 weeks'),('w','4 moths'),('m','9 months')])

    table, column, last_date = ReportHistoryWeekly, ReportHistoryWeekly.week, get_week_date_before(6)
    if filter_form.fields['duration'].initial == 'w':
        table, column, last_date = ReportHistoryMonthly, ReportHistoryMonthly.month, get_month_date_before(4)
    elif filter_form.fields['duration'].initial == 'm':
        table, column, last_date = ReportHistoryMonthly, ReportHistoryMonthly.month, get_month_date_before(9)

    problems = query_problems(db, table, column, last_date,\
                                filter_form.fields['os_release'].initial, filter_form.fields['component'].initial)

    forward = {"problems" : problems,
               "form" : filter_form}

    return render_to_response('problems/hot.html',\
                              forward,\
                              context_instance=RequestContext(request))

def summary(request, **kwargs):
    db = pyfaf.storage.getDatabase()
    problem = db.session.query(Problem).filter(Problem.id == kwargs["problem_id"]).first()
    report_ids = [report.id for report in problem.reports]

    sub = db.session.query(ReportOpSysRelease.opsysrelease_id,
                           func.sum(ReportOpSysRelease.count).label("cnt")) \
                    .join(Report) \
                    .filter(Report.id.in_(report_ids)) \
                    .group_by(ReportOpSysRelease.opsysrelease_id) \
                    .subquery()
    osreleases = db.session.query(OpSysRelease, sub.c.cnt).join(sub).all()

    sub = db.session.query(ReportArch.arch_id,
                           func.sum(ReportArch.count).label("cnt")) \
                    .join(Report) \
                    .filter(Report.id.in_(report_ids)) \
                    .group_by(ReportArch.arch_id) \
                    .subquery()
    arches = db.session.query(Arch, sub.c.cnt).join(sub).all()

    exes = db.session.query(ReportExecutable.path,
                            func.sum(ReportExecutable.count).label("cnt")) \
                    .join(Report) \
                    .filter(Report.id.in_(report_ids)) \
                    .group_by(ReportExecutable.path) \
                    .all()

    sub = db.session.query(ReportPackage.installed_package_id,
                           func.sum(ReportPackage.count).label("cnt")) \
                    .join(Report) \
                    .filter(Report.id.in_(report_ids)) \
                    .group_by(ReportPackage.installed_package_id) \
                    .subquery()
    packages = [(pkg.nevr(), cnt) for (pkg, cnt) in db.session.query(Package, sub.c.cnt).join(sub).all()]

    forward = { "problem": problem,
                "osreleases": osreleases,
                "arches": arches,
                "exes": exes,
                "packages": packages, }

    return render_to_response('problems/summary.html', forward, context_instance=RequestContext(request))

def backtraces(request):
    return render_to_response('problems/backtraces.html', {}, context_instance=RequestContext(request))

def cluster(request):
    return render_to_response('problems/cluster.html', {}, context_instance=RequestContext(request))
