ACLOCAL_AMFLAGS = -I m4

SUBDIRS = config src tests

EXTRA_DIST = autogen.sh gen-version faf-version faf.spec.in \
             init-scripts/faf-celery-beat.service \
             init-scripts/faf-celery-worker.service \
             init-scripts/faf-celery-tmpfiles.conf



if HAVE_SYSTEMD
systemdsystemunitdir=/usr/lib/systemd/system/
systemdsystemunit_DATA = init-scripts/faf-celery-beat.service \
                         init-scripts/faf-celery-worker.service
tmpfilesddir=/usr/lib/tmpfiles.d/
tmpfilesd_DATA = init-scripts/faf-celery-tmpfiles.conf
endif

RPM_DIRS = --define "_sourcedir `pwd`" \
           --define "_rpmdir `pwd`" \
           --define "_specdir `pwd`" \
           --define "_builddir `pwd`" \
           --define "_srcrpmdir `pwd`"

rpm: dist-xz faf.spec
	rpmbuild $(RPM_DIRS) -ba faf.spec

srpm: dist-xz faf.spec
	rpmbuild $(RPM_DIRS) -bs faf.spec
