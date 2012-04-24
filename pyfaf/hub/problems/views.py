import datetime
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.conf import settings
from ..summary.forms import ChartForm
from sqlalchemy import func
from sqlalchemy.sql.expression import desc
import pyfaf
from pyfaf.storage.problem import *
from pyfaf.storage.report import *
from pyfaf.storage.opsys import *

def query_problems(db, hist_table, hist_column, last_date, opsys, component):
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
            .filter(count_query.c.id==Problem.id)\
            .filter(rank_query.c.id==Problem.id)\
            .order_by(desc(rank_query.c.rank))

    if opsys:
        final_query\
            .join(Report)\
            .join(OpSysComponent)\
            .join(OpSys)\
            .join(OpSysRelease)\
            .filter(OpSysRelease.version==opsys)

    if component:
        if not opsys:
            final_query.join(Report).join(OpSysComponent)
        final_query.filter(OpSysComponent.name==component)

    return final_query.all()

def get_week_date_before(nweeks):
    curdate = datetime.date.today()
    return curdate - datetime.timedelta(weeks=nweeks,days=curdate.weekday())

def get_month_date_before(nmonths):
    return datetime.date.today().replace(day=1) - datetime.timdelta(months=nmonths)

def hot(request):
    db = pyfaf.storage.getDatabase()
    chartform = ChartForm(db, request.REQUEST)

    table, column, last_date = ReportHistoryDaily, ReportHistoryDaily.day, datetime.date.today() - datetime.timedelta(days=7)
    if chartform.fields['duration'].initial == 'w':
        last_date =  datetime.date.today() - datetime.timedelta(days=14)
    elif chartform.fields['duration'].initial == 'm':
        table, column, last_date = ReportHistoryWeekly, ReportHistoryWeekly.week, get_week_date_before(4)

    problems = query_problems(db, table, column, last_date, chartform.fields['os_release'].initial, chartform.fields['component'].initial)

    return render_to_response('problems/hot.html', {"problems":problems,"filter":chartform,"type":hot}, context_instance=RequestContext(request))

def longterm(request):
    db = pyfaf.storage.getDatabase()
    chartform = ChartForm(db, request.REQUEST)

    table, column, last_date = ReportHistoryWeekly, ReportHistoryWeekly.week, get_week_date_before(6)
    if chartform.fields['duration'].initial == 'w':
        table, column, last_date = ReportHistoryMonthly, ReportHistoryMonthly.month, get_month_date_before(4)
    elif chartform.fields['duration'].initial == 'm':
        table, column, last_date = ReportHistoryMonthly, ReportHistoryMonthly.month, get_month_date_before(9)

    problems = query_problems(db, table, column, last_date, chartform.fields['os_release'].initial, chartform.fields['component'].initial)

    return render_to_response('problems/hot.html', {"problems":problems,"filter":chartform,"type":longterm}, context_instance=RequestContext(request))

def summary(request, problem_id):
    return render_to_response('problems/summary.html', {}, context_instance=RequestContext(request))

def backtraces(request):
    return render_to_response('problems/backtraces.html', {}, context_instance=RequestContext(request))

def cluster(request):
    return render_to_response('problems/cluster.html', {}, context_instance=RequestContext(request))
