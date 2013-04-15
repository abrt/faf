#=============================================================================
# Config
#=============================================================================

SUBDIRS = plugins templates

config_DATA = faf.conf
configdir = $(sysconfdir)/faf

EXTRA_DIST = faf.conf.in

faf.conf: faf.conf.in
	 sed -e 's|@localstatedir[@]|$(localstatedir)|g' \
	     -e 's|@sysconfdir[@]|$(sysconfdir)|g' $< > $@
