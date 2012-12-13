import datetime
import os
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from pyfaf.config import CONFIG
from pyfaf.storage import *
from pyfaf.hub.common.utils import paginate
from sqlalchemy.sql.expression import desc

UNITS = ["B", "kB", "MB", "GB", "TB", "PB", "EB"]
def human_readable_size(bytes):
    size = float(bytes)
    unit = 0
    while size > 1024.0 and unit < len(UNITS) - 1:
        unit += 1
        size /= 1024.0

    return "%.2f %s" % (size, UNITS[unit])

def index(request):
    return render_to_response('status/index.html', {}, context_instance=RequestContext(request))

def builds(request):
    return render_to_response('status/builds.html', {}, context_instance=RequestContext(request))

def llvm(request):
    db = getDatabase()
    llvm_builds = db.session.query(LlvmBuild).order_by(desc(LlvmBuild.started)).all()
    llvm_builds = paginate(llvm_builds, request)

    for llvm_build in llvm_builds.object_list:
        llvm_build.add_nvr()
        llvm_build.add_human_readable_duration()
        llvm_build.count_bcfiles()

    return render_to_response('status/llvm.html',
                              {"builds": llvm_builds},
                              context_instance=RequestContext(request))

def llvm_details(request, *args, **kwargs):
    db = getDatabase()
    llvm_build_id = int(kwargs["llvm_build_id"])

    llvm_build = db.session.query(LlvmBuild).filter(LlvmBuild.id == llvm_build_id).one()
    llvm_build.add_nvr()
    llvm_build.add_human_readable_duration()
    llvm_build.count_bcfiles()
    stdout = llvm_build.get_lob("stdout")
    stderr = llvm_build.get_lob("stderr")
    packages = llvm_build.get_lob("packages")
    bcfiles = llvm_build.bc_files
    for bcfile in bcfiles:
        bcfile.size = human_readable_size(os.path.getsize(bcfile.get_lob_path("bcfile")))

    return render_to_response('status/llvm_details.html',
                              { "build": llvm_build,
                                "bcfiles": bcfiles,
                                "stdout": stdout,
                                "stderr": stderr,
                                "packages": packages },
                              context_instance=RequestContext(request))

def llvm_bcfile(request, *args, **kwargs):
    db = getDatabase()
    fileid = int(kwargs["fileid"])

    bcfile = db.session.query(LlvmBcFile).filter(LlvmBcFile.id == fileid).one()
    filename = bcfile.path
    if os.path.sep in filename:
        filename = filename.rsplit(os.path.sep, 1)[1]

    response = HttpResponse(mimetype='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename="{0}"'.format(filename)
    response['Content-Length'] = os.path.getsize(bcfile.get_lob_path("bcfile"))
    response.write(bcfile.get_lob("bcfile", binary=True))

    return response

def llvm_lob(request, *args, **kwargs):
    db = getDatabase()
    llvm_build_id = int(kwargs["llvm_build_id"])

    llvm_build = db.session.query(LlvmBuild).filter(LlvmBuild.id == llvm_build_id).one()
    lob = llvm_build.get_lob(kwargs["lob_name"])

    response = HttpResponse(mimetype='text/plain')
    response['Content-Length'] = len(lob)
    response.write(lob)

    return response
