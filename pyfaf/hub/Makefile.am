SUBDIRS = templates xmlrpc summary problems media reports status common

hub_PYTHON = hub.wsgi __init__.py menu.py settings.py urls.py
hubdir = $(pythondir)/pyfaf/hub

httpdconf_DATA = faf-hub.conf
httpdconfdir = ${sysconfdir}/httpd/conf.d

EXTRA_DIST = faf-hub.conf.in

faf-hub.conf: faf-hub.conf.in
	sed -e "s|@PYTHONDIR@|$(pythondir)|g" $< > $@
