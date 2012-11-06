ACLOCAL_AMFLAGS = -I m4

SUBDIRS = bin config pyfaf tests wrappers

EXTRA_DIST = autogen.sh RELEASE faf.spec.in

UPLOAD_URI = kklic@fedorahosted.org:faf
.PHONY: upload
upload:
	make dist-gzip
	scp $(distdir).tar.gz $(UPLOAD_URI)
	make dist-zip
	scp $(distdir).zip $(UPLOAD_URI)
	make dist-xz
	scp $(distdir).tar.xz $(UPLOAD_URI)

RPM_DIRS = --define "_sourcedir `pwd`" \
           --define "_rpmdir `pwd`" \
           --define "_specdir `pwd`" \
           --define "_builddir `pwd`" \
           --define "_srcrpmdir `pwd`"

rpm: dist-xz faf.spec
	rpmbuild $(RPM_DIRS) -ba faf.spec
srpm: dist-xz faf.spec
	rpmbuild $(RPM_DIRS) -bs faf.spec
