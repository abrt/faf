ACLOCAL_AMFLAGS = -I m4

SUBDIRS = config src tests

EXTRA_DIST = autogen.sh faf-version faf.spec \
             init-scripts/faf-celery-beat.service \
             init-scripts/faf-celery-worker.service \
             init-scripts/faf-celery-tmpfiles.conf \
             pylintrc README.md



if HAVE_SYSTEMD
systemdsystemunitdir=/usr/lib/systemd/system/
systemdsystemunit_DATA = init-scripts/faf-celery-beat.service \
                         init-scripts/faf-celery-worker.service
tmpfilesddir=/usr/lib/tmpfiles.d/
tmpfilesd_DATA = init-scripts/faf-celery-tmpfiles.conf
endif
