SUBDIRS = templates xmlrpc

hub_PYTHON = hub.wsgi __init__.py manage.py menu.py settings_local.py settings.py urls.py
hubdir = $(datadir)/faf/hub

httpdconf_DATA = faf-hub.conf
httpdconfdir = ${sysconfdir}/httpd/conf.d

EXTRA_DIST = faf-hub.conf.in

faf-hub.conf: faf-hub.conf.in
	sed -e "s|@PYTHONDIR@|$(pythondir)|g" $< > $@