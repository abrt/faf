from django.shortcuts import render_to_response
from django.template import RequestContext
from sqlalchemy import func
from sqlalchemy.sql.expression import desc
import pyfaf
from pyfaf.storage.problem import *
from pyfaf.storage.report import *
from pyfaf.storage.opsys import *

def index(request):
    return render_to_response('reports/index.html', {}, context_instance=RequestContext(request))

def list(request):
    db = pyfaf.storage.getDatabase()
    reports = db.session.query(Report.id, Report.first_occurence.label("created"), Report.last_occurence.label("last_change"))\
        .order_by(desc("last_change"))\
        .all()
    return render_to_response('reports/list.html', {"reports":reports}, context_instance=RequestContext(request))

def item(request, report_id):
    db = pyfaf.storage.getDatabase()
    report = db.session.query(Report, OpSysComponent, OpSys).join(OpSysComponent).join(OpSys).filter(Report.id==report_id).first()
    history_select = lambda table : db.session.query(table).filter(table.report_id==report_id).all()
    daily_history = history_select(ReportHistoryDaily)
    weekly_history = history_select(ReportHistoryWeekly)
    monhtly_history = history_select(ReportHistoryMonthly)
    return render_to_response('reports/item.html', {"report":report,"daily_history":daily_history,"weekly_history":weekly_history,"monhtly_history":monhtly_history}, context_instance=RequestContext(request))
