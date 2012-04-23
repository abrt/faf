from django.shortcuts import render_to_response
from django.template import RequestContext
from sqlalchemy import func
from django.conf import settings
from forms import ChartForm
import pyfaf
from pyfaf.storage import ReportHistoryDaily, OpSysComponent

def index(request):
    os_release = "Fedora 17"
    component = "coreutils"
    db = pyfaf.storage.getDatabase()

    chartform = ChartForm()

    if request.method == "POST":
        chartform = ChartForm(request.POST)
        if request.POST['osrelease']:
            os_release = request.POST['osrelease']

        if request.POST['component']:
            component = request.POST['component']

    #pylint:disable=E1101
    # Instance of 'Database' has no 'ReportHistoryDaily' member (but
    # some types could not be inferred).
    per_component = db.session.query(ReportHistoryDaily.day, func.sum(ReportHistoryDaily.count)).\
        filter(OpSysComponent.name == component).\
        group_by(ReportHistoryDaily.day).\
        order_by(ReportHistoryDaily.day).all()

    return render_to_response("summary/index.html",
                              { "reports": per_component, "chartform": chartform },
                              context_instance=RequestContext(request))
