from django.shortcuts import render_to_response
from django.template import RequestContext

def index(request):
    return render_to_response('reports/index.html', {}, context_instance=RequestContext(request))

def list(request):
    return render_to_response('reports/list.html', {}, context_instance=RequestContext(request))

def item(request):
    return render_to_response('reports/item.html', {}, context_instance=RequestContext(request))
