import os
import pyfaf
import logging
from datetime import datetime

from pyfaf.hub.dumpdirs.forms import NewDumpDirForm

from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response, redirect
from django.views.decorators.csrf import csrf_exempt
from django.core.servers.basehttp import FileWrapper
from django.core.files import File


def index(request, *args, **kwargs):
    ddlocation = pyfaf.config.get('DumpDir.CacheDirectory')
    dumpdirs = ((datetime.fromtimestamp(os.path.getctime(os.path.join(ddlocation, dir_entry))), dir_entry) for dir_entry in os.listdir(ddlocation))

    return render_to_response('dumpdirs/index.html',
                              {'dumpdirs' : dumpdirs },
                              context_instance=RequestContext(request))


def is_user_allowed_to_get_dump_dir(user):
    '''Returns True if the user is allowed to download dump directory'''

    # Can be replaced by the condition 'if user is a maintainer of ABRT/Libreport/Satyr project'
    return user.is_staff

def item(request, **kwargs):
    if request.user.is_authenticated():
        # only few chosen users are allowed to download a dump dir
        if not is_user_allowed_to_get_dump_dir(request.user):
            return HttpResponse('You are not a member of the right group to see the dump directory', status=401);

        ddlocation = pyfaf.config.get('DumpDir.CacheDirectory')
        ddpath = os.path.join(ddlocation, os.path.basename(kwargs['dumpdir_name']))

        if not os.path.exists(ddpath) or not os.path.isfile(ddpath):
            return HttpResponse('The requested dump directory was not found', status=404)

        ddfw = FileWrapper(file(ddpath))

        response = HttpResponse(ddfw, content_type='application/octet-stream');
        response['Content-length'] = os.path.getsize(ddpath)
        return response
    else:
        return HttpResponse('You are not authorized to see the dump dirrectory', status=401);


class SocketFile(File):
    '''Makes PUT HTTP method handling more convenient
       http://kunxi.org/archives/2009/01/how-to-put-a-file-in-django/

       Only forward access is allowed
    '''

    def __init__(self, socket, size):
        super(SocketFile, self).__init__(socket)
        self._size = int(size)
        self._pos = 0

    def read(self, num_bytes=None):
        if num_bytes is None:
            num_bytes = self._size - self._pos
        else:
            num_bytes = min(num_bytes, self._size - self._pos)
        self._pos += num_bytes
        return self.file.read(num_bytes)

    def tell(self):
        return self._pos

    def seek(self, position):
        pass


@csrf_exempt
def new(request, **kwargs):
    dumpdir_data = None
    form = None

    if request.method == 'PUT':
        dumpdir_data = SocketFile(request.environ['wsgi.input'], request.META['CONTENT_LENGTH'])
        dumpdir_data.name = os.path.basename(kwargs['dumpdir_name'])
    elif request.method == 'POST':
        form = NewDumpDirForm(request.POST, request.FILES)
        if form.is_valid():
            dumpdir_data = request.FILES['file']
        else:
            err = form.errors['file'][0]
            return HttpResponse(err, status=400)

    if dumpdir_data:
        max_dd_size = ddlocation = pyfaf.config.get('DumpDir.MaxDumpDirSize')
        if dumpdir_data.size > max_dd_size:
            err = "Dump dir archive may only be {0} bytes long".format(max_dd_size)
            return HttpResponse(err, status=413)

        # TODO: check name template abrt-upload-2013-02-19-13\:45\:49-8264.tar.gz
        ddlocation = pyfaf.config.get('DumpDir.CacheDirectory')
        ddquota = float(pyfaf.config.get('DumpDir.CacheDirectorySizeQuota'))

        used_space = 0.0
        try:
            used_space = sum((float(os.path.getsize(os.path.join("/tmp", x))) for x in os.listdir("/tmp")))
        except os.error as ex:
            logging.exception(ex)
            return HttpResponse('Some troubles with disk space.', status=500)

        if (ddquota - dumpdir_data.size) < used_space:
            err = "Out of disk space."
            loggin.warning(err)
            return HttpResponse(err, status=413)

        fname = os.path.join(ddlocation, dumpdir_data.name)
        if os.path.exists(fname):
            return HttpResponse("Dump dir archive already exists", status=409)

        with open(fname, 'w') as fil:
            for chunk in dumpdir_data.chunks():
                fil.write(chunk)

        if not form:
            return HttpResponse(reverse('pyfaf.hub.dumpdirs.views.item', args=[dumpdir_data.name]),
                                status=201)
    else:
        form = NewDumpDirForm()

    return render_to_response('dumpdirs/new.html', {'form': form},
        context_instance=RequestContext(request))


def delete(request, **kwargs):
    if request.user.is_authenticated():
        logging.info("User {0} attempts to delte dump dir {1}"
                        .format(request.user.username, kwargs['dumpdir_name']))

        # everyone authenticated is allowed to delete any dump directory
        # NOT only members of some chosen group (an user can ask someone involved
        #                                        to delete his private data)
        ddlocation = pyfaf.config.get('DumpDir.CacheDirectory')
        ddpath = os.path.join(ddlocation, os.path.basename(kwargs['dumpdir_name']))

        if not os.path.exists(ddpath) or not os.path.isfile(ddpath):
            return HttpResponse('The requested dump directory was not found',
                    status=404)

        try:
            os.remove(ddpath)
        except OSError as ex:
            logging.exception(ex)
            return HttpResponse('Can not delete the dump directory. '\
                'The dumpdirectory was probably delete. If the dump '\
                'directory is still present, please, contact the administrator.',
                status=500)

        return redirect(reverse(pyfaf.hub.dumpdirs.views.index))
