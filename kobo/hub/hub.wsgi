# -*- coding: utf-8 -*-


import os
import sys


# tweak PYTHONPATH if needed (usually if project is deployed outside site-packages)
sys.path.append("/usr/share/faf")

os.environ['DJANGO_SETTINGS_MODULE'] = 'hub.settings'
import django.core.handlers.wsgi


application = django.core.handlers.wsgi.WSGIHandler()
