from django.shortcuts import render_to_response
from django.template import RequestContext
from sqlalchemy import func
from sqlalchemy.sql.expression import desc
from sqlalchemy.sql.expression import literal
from sqlalchemy.sql.expression import literal_column
import pyfaf
from pyfaf.storage.report import Report, ReportOpSysRelease
from ..common.forms import DurationOsComponentFilterForm
from forms import ReportFilterForm

def index(request):
    db = pyfaf.storage.getDatabase()
    filter_form = DurationOsComponentFilterForm(db, request.REQUEST, [("d","days"),("w","weeks"),("m","months")])

    forward = {"chart_data" : None,\
               "filter" : filter_form}

    return render_to_response('reports/index.html', forward, context_instance=RequestContext(request))

def list(request):
    db = pyfaf.storage.getDatabase()
    filter_form = ReportFilterForm(db, request.REQUEST)

    statuses = db.session.query(Report.id, literal("NEW").label("status")).filter(Report.problem_id==None).subquery()

    if filter_form.fields['status'].initial == 1:
        statuses = db.session.query(Report.id, literal("FIXED").label("status")).filter(Report.problem_id!=None).subquery()

    reports = db.session.query(Report.id, statuses.c.status, Report.first_occurence.label("created"), Report.last_occurence.label("last_change"))\
        .join(ReportOpSysRelease)\
        .filter(statuses.c.id==Report.id)\
        .filter(ReportOpSysRelease.opsysrelease_id==filter_form.fields['os_release'].initial)\
        .order_by(desc("last_change"))

    if filter_form.fields['component'].initial >= 0:
        reports = reports.filter(Report.component_id==filter_form.fields['component'].initial)

    reports = reports.all()

    forward = {"reports" : reports,\
               "filter"  : filter_form}

    return render_to_response('reports/list.html', forward, context_instance=RequestContext(request))

def item(request, report_id):
    db = pyfaf.storage.getDatabase()
    report = db.session.query(Report, OpSysComponent, OpSys).join(OpSysComponent).join(OpSys).filter(Report.id==report_id).first()
    history_select = lambda table : db.session.query(table).filter(table.report_id==report_id).all()
    daily_history = history_select(ReportHistoryDaily)
    weekly_history = history_select(ReportHistoryWeekly)
    monhtly_history = history_select(ReportHistoryMonthly)
    return render_to_response('reports/item.html', {"report":report,"daily_history":daily_history,"weekly_history":weekly_history,"monhtly_history":monhtly_history}, context_instance=RequestContext(request))
