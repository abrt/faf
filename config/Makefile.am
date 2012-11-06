#=============================================================================
# Config
#=============================================================================

config_DATA = config
configdir = $(sysconfdir)/faf

httpd_DATA = faf.conf
httpddir = $(sysconfdir)/httpd/conf.d

EXTRA_DIST = faf.conf.in config.in

config: config.in
	 sed -e 's|@localstatedir[@]|$(localstatedir)|g' $< > $@

faf.conf: faf.conf.in
	 sed -e 's|@bindir[@]|$(bindir)|g' $< > $@
