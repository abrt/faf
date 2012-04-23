from django.shortcuts import render_to_response
from django.template import RequestContext
from sqlalchemy import func
import pyfaf
from pyfaf.storage.problem import *
from pyfaf.storage.report import *

def index(request):
    return render_to_response('reports/index.html', {}, context_instance=RequestContext(request))

def list(request):
    db = pyfaf.storage.getDatabase()
    reports = db.session.query(Report.id, Report.first_occurence.label("created"), Report.last_occurence.label("last_change")).all();
    return render_to_response('reports/list.html', {"reports":reports}, context_instance=RequestContext(request))

def item(request, report_id):
    db = pyfaf.storage.getDatabase()
    report = db.session.query(Report).filter(Report.id==report_id)
    return render_to_response('reports/item.html', {"report":report}, context_instance=RequestContext(request))
