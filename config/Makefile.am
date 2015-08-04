#=============================================================================
# Config
#=============================================================================

SUBDIRS = plugins templates

config_DATA = faf.conf
configdir = $(sysconfdir)/faf

faf.conf: faf.conf.in
	 sed -e 's|@localstatedir[@]|$(localstatedir)|g' \
	     -e 's|@sysconfdir[@]|$(sysconfdir)|g' $< > $@

httpdconf_DATA = faf-web2.conf
httpdconfdir = ${sysconfdir}/httpd/conf.d

faf-web2.conf: faf-web2.conf.in
	sed -e "s|@PYTHONDIR@|$(pythondir)|g" $< > $@

EXTRA_DIST = faf.conf.in \
             faf-web2.conf.in
