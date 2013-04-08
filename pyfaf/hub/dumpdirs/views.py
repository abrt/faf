import os
import pyfaf
import logging
from datetime import datetime

from pyfaf.hub.dumpdirs.forms import NewDumpDirForm

from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.template import RequestContext
from django.shortcuts import render_to_response, redirect
from django.views.decorators.csrf import csrf_exempt
from django.core.servers.basehttp import FileWrapper
from django.core.files import File


def check_user_rights(request, function_name, args):
    '''Returns True if the user is allowed to work with dump directories'''

    logger = logging.getLogger('pyfaf.hub.dumpdirs')
    logger.info('{0}: called {1}({2})'.format(request.user.username,
                                               function_name,
                                               args))

    if not request.user.is_authenticated() or not request.user.is_staff:
        raise Http404()


def index(request, **kwargs):
    check_user_rights(request, 'list_dump_directories', kwargs)

    dumpdirs = []
    ddlocation = pyfaf.config.get('DumpDir.CacheDirectory')
    if not os.path.exists(ddlocation):
        logging.error("Missing dump location '{0}'".format(ddlocation))
    else:
        dumpdirs = ((datetime.fromtimestamp(os.path.getctime(full_path)),
                     dir_entry,
                     os.path.getsize(full_path))
                         for dir_entry, full_path
                         in map(lambda base_name: (base_name,
                                                   os.path.join(ddlocation,
                                                                base_name)),
                                os.listdir(ddlocation)))
        dumpdirs = sorted(dumpdirs, key=lambda dentry: dentry[0])

    return render_to_response('dumpdirs/index.html',
                              {'dumpdirs' : dumpdirs},
                              context_instance=RequestContext(request))


def item(request, **kwargs):
    check_user_rights(request, 'download', kwargs)

    ddlocation = pyfaf.config.get('DumpDir.CacheDirectory')
    ddpath = os.path.join(ddlocation, os.path.basename(kwargs['dumpdir_name']))

    if not os.path.exists(ddpath) or not os.path.isfile(ddpath):
        return HttpResponse('The requested dump directory was not found',
                            status=404)

    ddfw = FileWrapper(file(ddpath))

    response = HttpResponse(ddfw, content_type='application/octet-stream');
    response['Content-length'] = os.path.getsize(ddpath)
    return response


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
        dumpdir_data = SocketFile(request.environ['wsgi.input'],
                                  request.META['CONTENT_LENGTH'])
        dumpdir_data.name = os.path.basename(kwargs['dumpdir_name'])
    elif request.method == 'POST':
        form = NewDumpDirForm(request.POST, request.FILES)
        if form.is_valid():
            dumpdir_data = request.FILES['file']
        else:
            err = form.errors['file'][0]
            return HttpResponse(err, status=400)

    if dumpdir_data:
        # TODO: check name template abrt-upload-2013-02-19-13\:45\:49-8264.tar.gz
        # TODO: compute a hash and do not allow to upload the same archive twice
        #       caching? atomicity? -> a new database table
        logger = logging.getLogger('pyfaf.hub.dumpdirs')
        ddlocation = pyfaf.config.get('DumpDir.CacheDirectory')
        if os.path.exists(ddlocation):
            logging.error("Missing dump location '{0}'".format(ddlocation))
            return HttpResponse('Thats embarrasing! We have some troubles'
                                ' with deployment. Please, try to upload'
                                ' your data later.',
                                status=500)

        count_dds = 0
        try:
            count_dds = sum((1 for x in os.listdir(ddlocation)
                                     if os.path.isfile(
                                           os.path.join(ddlocation, x))))
        except Exception as ex:
            logger.exception(ex)
            return HttpResponse('Thats embarrasing! We have some troubles'
                                ' with file system. Please, try to upload'
                                ' your data later.',
                                status=500)

        ddcountquota = int(pyfaf.config.get('DumpDir.CacheDirectoryCountQuota'))
        if count_dds >= ddcountquota:
            err ='Thats embarrasing! We have reached the'\
                 ' number of processed problems at time.'
            logger.warning(err)
            return HttpResponse(err, status=503)

        ddmaxsize = long(pyfaf.config.get('DumpDir.MaxDumpDirSize'))
        if dumpdir_data.size > ddmaxsize:
            return HttpResponse("Dump dir archive may only be {0} bytes long"
                                    .format(ddmaxsize),
                                status=413)

        used_space = 0.0
        try:
            used_space = sum((float(os.path.getsize(x))
                              for x in map(lambda f: os.path.join(ddlocation, f),
                                           os.listdir(ddlocation))
                                    if os.path.isfile(x)))
        except Exception as ex:
            logger.exception(ex)
            return HttpResponse('Thats embarrasing! We have some troubles'
                                ' with disk space. Please, try to upload'
                                ' your data later.',
                                status=500)

        ddquota = float(pyfaf.config.get('DumpDir.CacheDirectorySizeQuota'))
        if (ddquota - dumpdir_data.size) < used_space:
            err = "Thats embarrasing! We ran out of disk space."
            logger.warning(err)
            return HttpResponse(err, status=413)

        fname = os.path.join(ddlocation, dumpdir_data.name)
        if os.path.exists(fname):
            return HttpResponse("Dump dir archive already exists.",
                                status=409)

        with open(fname, 'w') as fil:
            for chunk in dumpdir_data.chunks():
                fil.write(chunk)

        if not form:
            return HttpResponse(reverse('pyfaf.hub.dumpdirs.views.item',
                                        args=[dumpdir_data.name]),
                                status=201)
    else:
        form = NewDumpDirForm()

    return render_to_response('dumpdirs/new.html', {'form': form},
        context_instance=RequestContext(request))


def delete(request, **kwargs):
    check_user_rights(request, 'delete', kwargs)

    ddlocation = pyfaf.config.get('DumpDir.CacheDirectory')
    ddpath = os.path.join(ddlocation, os.path.basename(kwargs['dumpdir_name']))

    if not os.path.exists(ddpath) or not os.path.isfile(ddpath):
        return HttpResponse('The requested dump directory was not found',
                status=404)

    try:
        os.remove(ddpath)
    except OSError as ex:
        logger = logging.getLogger('pyfaf.hub.dumpdirs')
        logger.exception(ex)
        return HttpResponse('Can not delete the dump directory. '
            'The dumpdirectory was probably delete. If the dump '
            'directory is still present, please, contact the administrator.',
            status=500)

    return redirect(reverse(pyfaf.hub.dumpdirs.views.index))
