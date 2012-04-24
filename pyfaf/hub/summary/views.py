from django.shortcuts import render_to_response
from django.template import RequestContext
from sqlalchemy import func
from django.conf import settings
from django.contrib import messages
from forms import ChartForm
import pyfaf
from pyfaf.storage import ReportHistoryDaily, ReportHistoryWeekly, ReportHistoryMonthly, OpSysComponent, Report, OpSysRelease
import datetime

def months_ago(count):
    day = datetime.date.today()
    day = day.replace(day=1)
    month = day.month - count
    if month > 0:
        day = day.replace(month=month)
    else:
        day = day.replace(year=day.year - 1, month = 12 + month)
    return day

def index(request):
    db = pyfaf.storage.getDatabase()
    chartform = ChartForm(db, request.REQUEST)

    #pylint:disable=E1101
    # Instance of 'Database' has no 'ReportHistoryDaily' member (but
    # some types could not be inferred).
    if chartform.fields['duration'].initial == 'd':
        historyQuery = db.session.query(ReportHistoryDaily.day,
            func.sum(ReportHistoryDaily.count)).\
            filter(ReportHistoryDaily.day > datetime.date.today() - datetime.timedelta(days=15)).\
            group_by(ReportHistoryDaily.day).\
            order_by(ReportHistoryDaily.day)
    elif chartform.fields['duration'].initial == 'w':
        historyQuery = db.session.query(ReportHistoryWeekly.week,
            func.sum(ReportHistoryWeekly.count)).\
            filter(ReportHistoryWeekly.week > datetime.date.today() - datetime.timedelta(weeks=9)).\
            group_by(ReportHistoryWeekly.week).\
            order_by(ReportHistoryWeekly.week)
    else:
        # chartform.fields['duration'].initial == 'm'
        historyQuery = db.session.query(ReportHistoryMonthly.month,
            func.sum(ReportHistoryMonthly.count)).\
            filter(ReportHistoryMonthly.month >= months_ago(12)).\
            group_by(ReportHistoryMonthly.month).\
            order_by(ReportHistoryMonthly.month)

    if chartform.fields['component'].initial == -1:
        # All Components
        # TODO: filter by opsysrelease
        historyQuery = historyQuery.all()
    else:
        # Selected Component
        # TODO: filter by opsysrelease
        historyQuery = historyQuery.join(Report, OpSysComponent).\
            filter(OpSysComponent.id == chartform.fields['component'].initial).\
            all()

    historyDict = dict(historyQuery)

    if chartform.fields['duration'].initial == 'd':
        for i in range(0, 14):
            day = datetime.date.today() - datetime.timedelta(days=i)
            if day not in historyDict:
                historyDict[day] = 0
    elif chartform.fields['duration'].initial == 'w':
        for i in range(0, 8):
            day = datetime.date.today()
            day -= datetime.timedelta(days=day.weekday()) + datetime.timedelta(weeks=i)
            if day not in historyDict:
                historyDict[day] = 0
    else:
        # chartform.fields['duration'].initial == 'm'
        for i in range(0, 12):
            day = months_ago(i)
            if day not in historyDict:
                historyDict[day] = 0

    reports = sorted(historyDict.items(), key=lambda x: x[0])

    return render_to_response("summary/index.html",
                              { "reports": reports,
                                "chartform": chartform,
                                "duration": chartform.fields['duration'].initial },
                              context_instance=RequestContext(request))
