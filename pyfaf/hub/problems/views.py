from django.shortcuts import render_to_response
from django.template import RequestContext

def hot(request):
    return render_to_response('problems/hot.html', {}, context_instance=RequestContext(request))

def longterm(request):
    return render_to_response('problems/longterm.html', {}, context_instance=RequestContext(request))

def summary(request):
    return render_to_response('problems/summary.html', {}, context_instance=RequestContext(request))

def backtraces(request):
    return render_to_response('problems/backtraces.html', {}, context_instance=RequestContext(request))

def cluster(request):
    return render_to_response('problems/cluster.html', {}, context_instance=RequestContext(request))
