emergency_PYTHON = emergency.wsgi __init__.py
emergencydir = $(pythondir)/pyfaf/emergency

httpdconf_DATA = faf-emergency.conf
httpdconfdir = ${sysconfdir}/httpd/conf.d

EXTRA_DIST = faf-emergency.conf.in

faf-emergency.conf: faf-emergency.conf.in
	sed -e "s|@PYTHONDIR@|$(pythondir)|g" $< > $@
