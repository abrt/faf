import datetime
from django.shortcuts import render_to_response
from django.template import RequestContext
from sqlalchemy import func
from sqlalchemy.sql.expression import desc, literal, literal_column, distinct, Alias
import pyfaf
from pyfaf.storage.opsys import OpSys, OpSysComponent
from pyfaf.storage.report import Report, ReportOpSysRelease, ReportHistoryDaily, ReportHistoryWeekly, ReportHistoryMonthly
from pyfaf.hub.reports.forms import ReportFilterForm, ReportOverviewConfigurationForm

def date_iterator(first_date, time_unit="d", end_date=None):
    if time_unit == "d":
        next_date_fn = lambda x : x + datetime.timedelta(days=1)
    elif time_unit == "w":
        first_date -= datetime.timedelta(days=first_date.weekday())
        next_date_fn = lambda x : x + datetime.timedelta(weeks=1)
    elif time_unit == "m":
        first_date = first_date.replace(day=1)
        next_date_fn = lambda x : (x.replace(day=25) + datetime.timedelta(days=7)).replace(day=1)
    else:
        raise ValueError("Unkonwn time unit type : '%s'" % time_unit)

    toreturn = first_date
    yield toreturn
    while True:
        toreturn = next_date_fn(toreturn)
        if not end_date is None and toreturn>end_date:
            break

        yield toreturn

def chart_data_generator(chart_data, dates):
    last_value = 0
    reports = iter(chart_data)
    report = next(reports)

    for date in dates:
        if date < report[0]:
            yield (date,last_value)
        else:
            last_value = report[1]
            yield report
            report = next(reports)

def index(request):
    db = pyfaf.storage.getDatabase()
    filter_form = ReportOverviewConfigurationForm(db, request.REQUEST)

    duration_opt = filter_form.fields['duration'].initial
    if duration_opt == "d":
        hist_column = ReportHistoryDaily.day
        hist_table = ReportHistoryDaily
    elif duration_opt == "w":
        hist_column = ReportHistoryWeekly.week
        hist_table = ReportHistoryWeekly
    elif duration_opt == "m":
        hist_column = ReportHistoryMonthly.month
        hist_table = ReportHistoryMonthly
    else:
        raise ValueError("Unknown duration option : '%s'" % duration_opt)

    os_release_id = filter_form.fields['os_release'].initial
    counts_per_date = db.session.query(hist_column.label("time"),func.sum(hist_table.count).label("count"))\
            .join(ReportOpSysRelease, ReportOpSysRelease.report_id==hist_table.report_id)\
            .filter((ReportOpSysRelease.opsysrelease_id==os_release_id) | (os_release_id==-1))\
            .group_by(hist_column)

    if filter_form.fields['component'].initial != -1:
        counts_per_date = counts_per_date.outerjoin(Report, Report.id==ReportOpSysRelease.report_id)\
                .filter((Report.component_id==filter_form.fields['component'].initial))

    counts_per_date = counts_per_date.subquery()

    hist_dates = db.session.query(distinct(hist_column).label("time"))\
            .subquery()

    accumulated_date_counts = db.session.query(hist_dates.c.time, func.sum(counts_per_date.c.count))\
                    .filter(hist_dates.c.time>=counts_per_date.c.time)\
                    .group_by(hist_dates.c.time)\
                    .order_by(hist_dates.c.time)\
                    .all();

    hist_mindate = db.session.query(func.min(hist_column).label("value")).one()
    hist_mindate = hist_mindate[0] if not hist_mindate[0] is None  else datetime.date.today()

    displayed_dates = (d for d in date_iterator(hist_mindate, duration_opt, datetime.date.today()))

    if len(accumulated_date_counts) != 0:
        chart_data = (report for report in chart_data_generator(accumulated_date_counts, displayed_dates))
    else:
        chart_data = ((date,0) for date in displayed_dates)

    forward = {"reports" : chart_data,
               "duration" : duration_opt,
               "form" : filter_form}

    return render_to_response('reports/index.html', forward, context_instance=RequestContext(request))

def list(request):
    db = pyfaf.storage.getDatabase()
    filter_form = ReportFilterForm(db, request.REQUEST)

    statuses = db.session.query(Report.id, literal("NEW").label("status")).filter(Report.problem_id==None).subquery()

    if filter_form.fields['status'].initial == 1:
        statuses = db.session.query(Report.id, literal("FIXED").label("status")).filter(Report.problem_id!=None).subquery()

    opsysrelease_id = filter_form.fields['os_release'].initial
    reports = db.session.query(Report.id, statuses.c.status, Report.first_occurence.label("created"), Report.last_occurence.label("last_change"), OpSysComponent.name.label("component"))\
        .join(ReportOpSysRelease)\
        .join(OpSysComponent)\
        .filter(statuses.c.id==Report.id)\
        .filter((ReportOpSysRelease.opsysrelease_id==opsysrelease_id) | (opsysrelease_id==-1))\
        .order_by(desc("last_change"))

    if filter_form.fields['component'].initial >= 0:
        reports = reports.filter(Report.component_id==filter_form.fields['component'].initial)

    reports = reports.all()

    forward = {"reports" : reports,
               "form"  : filter_form}

    return render_to_response('reports/list.html', forward, context_instance=RequestContext(request))

def item(request, report_id):
    db = pyfaf.storage.getDatabase()
    report = db.session.query(Report, OpSysComponent, OpSys).join(OpSysComponent).join(OpSys).filter(Report.id==report_id).first()
    history_select = lambda table : db.session.query(table).filter(table.report_id==report_id).all()
    daily_history = history_select(ReportHistoryDaily)
    weekly_history = history_select(ReportHistoryWeekly)
    monhtly_history = history_select(ReportHistoryMonthly)
    return render_to_response('reports/item.html', {"report":report,"daily_history":daily_history,"weekly_history":weekly_history,"monhtly_history":monhtly_history}, context_instance=RequestContext(request))
