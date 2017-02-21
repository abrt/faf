#=============================================================================
# Config
#=============================================================================

SUBDIRS = plugins templates

config_DATA = faf.conf

if HAVE_SYSTEMD
  config_DATA += celery-beat-env.conf
  config_DATA += celery-worker-env.conf
endif

configdir = $(sysconfdir)/faf

faf.conf: faf.conf.in
	 sed -e 's|@localstatedir[@]|$(localstatedir)|g' \
	     -e 's|@sysconfdir[@]|$(sysconfdir)|g' $< > $@

httpdconf_DATA = faf-web.conf
httpdconfdir = ${sysconfdir}/httpd/conf.d

faf-web.conf: faf-web.conf.in
	sed -e "s|@PYTHONDIR@|$(pythondir)|g" $< > $@

logrotate_DATA = faf
logrotatedir = ${sysconfdir}/logrotate.d

EXTRA_DIST = celery-beat-env.conf \
             celery-worker-env.conf \
             faf.conf.in \
             faf-web.conf.in \
             faf
