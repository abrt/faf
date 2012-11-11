#=============================================================================
# Config
#=============================================================================

config_DATA = config
configdir = $(sysconfdir)/faf

httpd_DATA = faf.conf
httpddir = $(sysconfdir)/httpd/conf.d

libreport_DATA = faf_event.conf
libreportdir = $(sysconfdir)/libreport/events.d

EXTRA_DIST = faf.conf.in config.in faf_event.conf

config: config.in
	 sed -e 's|@localstatedir[@]|$(localstatedir)|g' $< > $@

faf.conf: faf.conf.in
	 sed -e 's|@bindir[@]|$(bindir)|g' $< > $@
