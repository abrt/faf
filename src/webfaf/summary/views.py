import datetime
import json

from django.template import RequestContext
from django.shortcuts import render_to_response, redirect
from django.http import HttpResponse

import webfaf
from pyfaf.storage import Report, getDatabase
from webfaf.common.forms import DurationOsComponentFilterForm
from webfaf.common.queries import ReportHistoryCounts
from webfaf.common.utils import WebfafJSONEncoder

class IncrementalHistory(ReportHistoryCounts):
    def __init__(self, db, osrelease_ids, component_ids, duration_opt):
        super(IncrementalHistory, self).__init__(db, osrelease_ids,
            component_ids, duration_opt)

    def generate_default_report(self, date):
        return (date, 0)

    def decorate_report_entry(self, report):
        return report

    def get_min_date(self):
        if self.duration_opt == "d":
            return datetime.date.today() - datetime.timedelta(days=14)
        elif self.duration_opt == "w":
            d = datetime.date.today()
            return d - datetime.timedelta(days=d.weekday(), weeks=8)
        elif self.duration_opt == "m":
            hist_mindate = datetime.date.today().replace(day=1)
            return hist_mindate.replace(year=(hist_mindate.year - 1))
        elif self.duration_opt == "*":
            hist_mindate = (self.db.session.query(Report.first_occurrence)
                .order_by(Report.first_occurrence)
                .first()[0])
            return hist_mindate.date() - datetime.timedelta(days=30)
        else:
            raise ValueError("Unknown duration option : '%s'" % self.duration_opt)

    def query_all(self, query_obj):
        return query_obj.filter(self.hist_column >= self.get_min_date()).all()

def index(request):
    return redirect(webfaf.summary.views.summary)

def summary(request, *args, **kwargs):
    db = getDatabase()
    params = dict(request.REQUEST)
    params.update(kwargs)
    form = DurationOsComponentFilterForm(db, params)

    #pylint:disable=E1101
    # Instance of 'Database' has no 'ReportHistoryDaily' member (but
    # some types could not be inferred).
    duration_opt = form.get_duration_selection()
    if duration_opt == "d":
        resolution_opt = "d"
    elif duration_opt == "w":
        resolution_opt = "d"
    elif duration_opt == "m":
        resolution_opt = "w"
    else:
        resolution_opt = "m"

    component_ids = form.get_component_selection()

    reports = ((name, IncrementalHistory(db,
                                         ids,
                                         component_ids,
                                         duration_opt).report_counts())
                for ids, name in form.get_release_selection())

    if "application/json" in request.META.get("HTTP_ACCEPT"):
        data = []
        for (name, report_counts) in reports:
            timeseries = []
            for (dt, count) in report_counts:
                timeseries.append({"date": dt, "count": count})
            data.append({"name": name,
                         "timeseries": timeseries})
        return HttpResponse(json.dumps(data, cls=WebfafJSONEncoder),
                            status=200, mimetype="application/json")

    else:
        return render_to_response("summary/index.html",
                                  {"reports": reports,
                                   "form": form,
                                   "resolution": resolution_opt},
                                  context_instance=RequestContext(request))
