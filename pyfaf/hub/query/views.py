import datetime
import os
import json
import pyfaf
from django.http import HttpResponse, Http404
from pyfaf.storage import *
from sqlalchemy.orm.attributes import InstrumentedAttribute

def objects(request, *args, **kwargs):
    result = {}
    db = getDatabase()

    objnames = kwargs.pop("objnames")
    for objname in objnames.split(";"):
        # hack, do not query django internals
        if objname in pyfaf.storage.__dict__ and not objname in pyfaf.storage.hub.__dict__:
            obj = pyfaf.storage.__dict__[objname]
            objs = db.session.query(obj).all()
            result[objname] = [o.id for o in objs]

    result_json = json.dumps(result)
    response = HttpResponse(mimetype="application/json")
    response['Content-Length'] = len(result_json)
    response.write(result_json)

    return response

def objects_details(request, *args, **kwargs):
    result = {}
    db = getDatabase()

    objname = kwargs.pop("objname")
    # hack, do not query django internals
    if not objname in pyfaf.storage.__dict__ or objname in pyfaf.storage.hub.__dict__:
        raise Http404

    obj = pyfaf.storage.__dict__[objname]

    objids = kwargs.pop("objids")
    for objid in objids.split(";"):
        try:
            objid = int(objid)
            instance = db.session.query(obj).filter(obj.id == objid).one()
        except:
            continue

        result[objid] = {}

        for col in obj.__table__.columns:
            if col.name == "id":
                continue

            value = getattr(instance, col.name)
            if isinstance(value, datetime.datetime):
                value = str(value)

            result[objid][col.name] = value

        for elem in obj.__dict__:
            if isinstance(getattr(obj, elem), InstrumentedAttribute) and elem != "id" and not elem in result[objid]:
                value = getattr(instance, elem)
                if isinstance(value, list):
                    result[objid][elem] = [o.id for o in value]

    result_json = json.dumps(result)
    response = HttpResponse(mimetype="application/json")
    response['Content-Length'] = len(result_json)
    response.write(result_json)

    return response
