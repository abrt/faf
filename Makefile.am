ACLOCAL_AMFLAGS = -I m4

SUBDIRS = config src tests

EXTRA_DIST = autogen.sh faf.spec.in \
             selinux/fafpolicy.fc \
             selinux/fafpolicy.if \
             selinux/fafpolicy.te

RPM_DIRS = --define "_sourcedir `pwd`" \
           --define "_rpmdir `pwd`" \
           --define "_specdir `pwd`" \
           --define "_builddir `pwd`" \
           --define "_srcrpmdir `pwd`"

rpm: dist-xz faf.spec
	rpmbuild $(RPM_DIRS) -ba faf.spec

srpm: dist-xz faf.spec
	rpmbuild $(RPM_DIRS) -bs faf.spec
