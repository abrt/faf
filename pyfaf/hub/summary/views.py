import datetime

from django.template import RequestContext
from django.shortcuts import render_to_response, redirect

from sqlalchemy import func

import pyfaf
from pyfaf.hub.common.forms import DurationOsComponentFilterForm
from pyfaf.hub.common.queries import ReportHistoryCounts

class IncrementalHistory(ReportHistoryCounts):
    def __init__(self, db, osrelease_ids, component_ids, duration_opt):
        super(IncrementalHistory, self).__init__(db, osrelease_ids, component_ids, duration_opt)

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
        else:
            raise ValueError("Unknown duration option : '%s'" % self.duration_opt)

    def query_all(self, query_obj):
        return query_obj.filter(self.hist_column >= self.get_min_date()).all()

def index(request):
    return redirect(pyfaf.hub.summary.views.summary);

def summary(request, *args, **kwargs):
    db = pyfaf.storage.getDatabase()
    params = dict(request.REQUEST)
    params.update(kwargs)
    form = DurationOsComponentFilterForm(db, params)

    #pylint:disable=E1101
    # Instance of 'Database' has no 'ReportHistoryDaily' member (but
    # some types could not be inferred).
    duration_opt = form.get_duration_selection()
    component_ids = form.get_component_selection()

    reports = ((name, IncrementalHistory(db,
                                         ids,
                                         component_ids,
                                         duration_opt).report_counts())
                for ids, name in form.get_release_selection())

    return render_to_response("summary/index.html",
                              { "reports": reports,
                                "form": form,
                                "duration": duration_opt },
                              context_instance=RequestContext(request))
