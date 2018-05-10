ACLOCAL_AMFLAGS = -I m4

SUBDIRS = config src tests

EXTRA_DIST = autogen.sh gen-version faf-version faf.spec.in \
             init-scripts/faf-celery-beat.service \
             init-scripts/faf-celery-worker.service \
             init-scripts/faf-celery-tmpfiles.conf \
             pylintrc



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

rpm:
	$(MAKE) dist
	rpmbuild $(RPM_DIRS) -ba faf.spec

srpm:
	$(MAKE) dist
	rpmbuild $(RPM_DIRS) -bs faf.spec

# value for overriding from command line
# e.g: make scratch-build DIST=f15
DIST=rawhide
scratch-build: srpm
	koji build --scratch $(DIST) `make srpm | grep Wrote | cut -d' ' -f2`

UPLOAD_URL ?= localhost

upload: dist
	scp $(distdir).tar.gz $$(test -n "$$UPLOAD_LOGIN" && echo "$$UPLOAD_LOGIN@")$(UPLOAD_URL)

.PHONY: release-fix
release-fix:
	OLD_VER=$$(git describe --tags --match "[0-9]*" --abbrev=0 HEAD 2>/dev/null); \
	MAJOR_VER=$$(echo $$OLD_VER | cut -d. -f 1); \
	MINOR_VER=$$(echo $$OLD_VER | cut -d. -f 2); \
	FIX_VER=$$(echo $$OLD_VER | cut -d. -f 3); \
	$(MAKE) release OLD_VER=$$OLD_VER NEW_VER="$$MAJOR_VER.$$MINOR_VER.$$((FIX_VER+1))"

.PHONY: release-minor
release-minor:
	OLD_VER=$$(git describe --tags --match "[0-9]*" --abbrev=0 HEAD 2>/dev/null); \
	MAJOR_VER=$$(echo $$OLD_VER | cut -d. -f 1); \
	MINOR_VER=$$(echo $$OLD_VER | cut -d. -f 2); \
	$(MAKE) release OLD_VER=$$OLD_VER NEW_VER="$$MAJOR_VER.$$((MINOR_VER+1)).0"

.PHONY: release-major
release-major:
	OLD_VER=$$(git describe --tags --match "[0-9]*" --abbrev=0 HEAD 2>/dev/null); \
	MAJOR_VER=$$(echo $$OLD_VER | cut -d. -f 1); \
	$(MAKE) release OLD_VER=$$OLD_VER NEW_VER="$$((MAJOR_VER+1)).0.0"

.PHONY: release
release:
	echo "* $$(LANG='en.UTF-8' date +'%a %b %d %Y') $$(git config --get user.name) <$$(git config --get user.email)> $$NEW_VER-1" | sort > /tmp/changelog.tmp; \
	git log --oneline $$OLD_VER..HEAD | awk '{$$1=""; if (a[$$0]++ == 0) print "-" $$0} END {print ""}' | grep -v -e "- Merge" -e "- testsuite:" -e "- make:" -e "- tests:" -e "- docker:" >> /tmp/changelog.tmp; \
	sed "$$(grep -n changelog faf.spec.in | cut -f1 -d:| head -n 1)"'r /tmp/changelog.tmp' -i faf.spec.in; \
	sed -e "s/^## \[Unreleased\]/## [Unreleased]\n\n## [$$NEW_VER] - $$(date +'%F')/" \
	    -e "s/^\[Unreleased\]: \(https:\/\/.*\/compare\)\(\/.*\)\.\.\.HEAD/[Unreleased]: \1\/$$NEW_VER...HEAD\n[$$NEW_VER]: \1\2...$$NEW_VER/" \
	    -i CHANGELOG.md; \
	sed 's|DEF_VER=.*$$|DEF_VER='$$NEW_VER'|' -i gen-version; \
	git add gen-version faf.spec.in CHANGELOG.md; \
	git commit -m "New version $$NEW_VER"; \
	git tag "$$NEW_VER"; \
	echo -n "$$NEW_VER" > faf-version
	autoconf --force
	$(MAKE) dist
