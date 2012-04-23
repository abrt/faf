from django.shortcuts import render_to_response
from django.template import RequestContext

def index(request):
    return render_to_response('status/index.html', {}, context_instance=RequestContext(request))

def builds(request):
    return render_to_response('status/builds.html', {}, context_instance=RequestContext(request))

def llvm(request):
    return render_to_response('status/llvm.html', {}, context_instance=RequestContext(request))
