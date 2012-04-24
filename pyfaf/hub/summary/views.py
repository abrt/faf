from django.shortcuts import render_to_response
from django.template import RequestContext
from sqlalchemy import func
from django.conf import settings
from django.contrib import messages
from forms import ChartForm
import pyfaf
from pyfaf.storage import ReportHistoryDaily, ReportHistoryWeekly, ReportHistoryMonthly, OpSysComponent, Report, OpSysRelease

def index(request):
    db = pyfaf.storage.getDatabase()
    chartform = ChartForm(db, request.REQUEST)

    #pylint:disable=E1101
    # Instance of 'Database' has no 'ReportHistoryDaily' member (but
    # some types could not be inferred).
    if chartform.fields['duration'].initial == 'd':
        historyQuery = db.session.query(ReportHistoryDaily.day,
            func.sum(ReportHistoryDaily.count)).\
            group_by(ReportHistoryDaily.day).\
            order_by(ReportHistoryDaily.day)
    elif chartform.fields['duration'].initial == 'w':
        historyQuery = db.session.query(ReportHistoryWeekly.week,
            func.sum(ReportHistoryWeekly.count)).\
            group_by(ReportHistoryWeekly.week).\
            order_by(ReportHistoryWeekly.week)
    else:
        # chartform.fields['duration'].initial == 'm'
        historyQuery = db.session.query(ReportHistoryMonthly.month,
            func.sum(ReportHistoryMonthly.count)).\
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

    return render_to_response("summary/index.html",
                              { "reports": historyQuery,
                                "chartform": chartform,
                                "duration": chartform.fields['duration'].initial },
                              context_instance=RequestContext(request))
