from django.shortcuts import render_to_response
from django.template import RequestContext
from sqlalchemy import func
from django.conf import settings
from django.contrib import messages
import pyfaf
from pyfaf.storage import ReportHistoryDaily, ReportHistoryWeekly, ReportHistoryMonthly, OpSysComponent, Report, OpSysRelease, ReportOpSysRelease
import datetime
from ..common.forms import DurationOsComponentFilterForm

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
    form = DurationOsComponentFilterForm(db, request.REQUEST)

    #pylint:disable=E1101
    # Instance of 'Database' has no 'ReportHistoryDaily' member (but
    # some types could not be inferred).
    duration_opt = form.fields['duration'].initial
    component_id = form.fields['component'].initial

    reports = ((name, release_incremental_history(db, ids, component_id, duration_opt)) for ids, name in form.getOsReleseaSelection())

    return render_to_response("summary/index.html",
                              { "reports": reports,
                                "form": form,
                                "duration": duration_opt },
                              context_instance=RequestContext(request))

def release_incremental_history(db, osreleases_id, component_id, duration):
    if duration == 'd':
        hist_table = ReportHistoryDaily
        hist_column = ReportHistoryDaily.day
        historyQuery = db.session.query(ReportHistoryDaily.day,
            func.sum(ReportHistoryDaily.count)).\
            filter(ReportHistoryDaily.day > datetime.date.today() - datetime.timedelta(days=15)).\
            group_by(ReportHistoryDaily.day).\
            order_by(ReportHistoryDaily.day)
    elif duration == 'w':
        hist_table = ReportHistoryWeekly
        hist_column = ReportHistoryWeekly.week
        historyQuery = db.session.query(ReportHistoryWeekly.week,
            func.sum(ReportHistoryWeekly.count)).\
            filter(ReportHistoryWeekly.week > datetime.date.today() - datetime.timedelta(weeks=9)).\
            group_by(ReportHistoryWeekly.week).\
            order_by(ReportHistoryWeekly.week)
    else:
        hist_table = ReportHistoryMonthly
        hist_column = ReportHistoryMonthly.month
        # duration == 'm'
        historyQuery = db.session.query(ReportHistoryMonthly.month,
            func.sum(ReportHistoryMonthly.count)).\
            filter(ReportHistoryMonthly.month >= months_ago(12)).\
            group_by(ReportHistoryMonthly.month).\
            order_by(ReportHistoryMonthly.month)

    if len(osreleases_id) != 0:
        #FIXME : correct selection of OS release !!
        #Missing table RepostOpSysReleaseHistory(Daily|Weekly|Monthly)
        historyQuery = historyQuery.join(ReportOpSysRelease, ReportOpSysRelease.report_id==hist_table.report_id).\
            filter(ReportOpSysRelease.opsysrelease_id.in_(osreleases_id))

    if component_id != -1:
        # Selected Component
        historyQuery = historyQuery.join(Report, OpSysComponent).\
            filter(OpSysComponent.id == component_id)

    historyDict = dict(historyQuery.all())

    if duration == 'd':
        for i in range(0, 14):
            day = datetime.date.today() - datetime.timedelta(days=i)
            if day not in historyDict:
                historyDict[day] = 0
    elif duration == 'w':
        for i in range(0, 8):
            day = datetime.date.today()
            day -= datetime.timedelta(days=day.weekday()) + datetime.timedelta(weeks=i)
            if day not in historyDict:
                historyDict[day] = 0
    else:
        # duration == 'm'
        for i in range(0, 12):
            day = months_ago(i)
            if day not in historyDict:
                historyDict[day] = 0

    return sorted(historyDict.items(), key=lambda x: x[0])

