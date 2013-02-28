ACLOCAL_AMFLAGS = -I m4

SUBDIRS = bin config pyfaf tests wrappers

EXTRA_DIST = autogen.sh RELEASE faf.spec.in

RPM_DIRS = --define "_sourcedir `pwd`" \
           --define "_rpmdir `pwd`" \
           --define "_specdir `pwd`" \
           --define "_builddir `pwd`" \
           --define "_srcrpmdir `pwd`"

rpm: dist-xz faf.spec
	rpmbuild $(RPM_DIRS) -ba faf.spec
srpm: dist-xz faf.spec
	rpmbuild $(RPM_DIRS) -bs faf.spec

UPLOAD_URL ?= fedorahosted.org:faf

upload: dist
	scp $(distdir).tar.gz $$(test -n "$$UPLOAD_LOGIN" && echo "$$UPLOAD_LOGIN@")$(UPLOAD_URL)

.PHONY: release-minor
release-minor:
	OLD_VER=$$(git describe --tags --match "[0-9]*" --abbrev=0 HEAD 2>/dev/null); \
	MAJOR_VER=$$(echo $$OLD_VER | cut -d. -f 1); \
	MINOR_VER=$$(echo $$OLD_VER | cut -d. -f 2); \
	$(MAKE) release OLD_VER=$$OLD_VER NEW_VER="$$MAJOR_VER.$$((MINOR_VER+1))"

.PHONY: release-major
release-major:
	OLD_VER=$$(git describe --tags --match "[0-9]*" --abbrev=0 HEAD 2>/dev/null); \
	MAJOR_VER=$$(echo $$OLD_VER | cut -d. -f 1); \
	$(MAKE) release OLD_VER=$$OLD_VER NEW_VER="$$((MAJOR_VER+1)).0"

.PHONY: release
release:
	echo "* $$(date +'%a %b %d %Y') $$(git config --get user.name) <$$(git config --get user.email)> $$NEW_VER-1" > /tmp/changelog.tmp; \
	git log --oneline $$OLD_VER..HEAD | awk '{$$1=""; print "-" $$0} END {print ""}' >> /tmp/changelog.tmp; \
	sed "$$(grep -n changelog faf.spec.in | cut -f1 -d:)"'r /tmp/changelog.tmp' -i faf.spec.in; \
	git add faf.spec.in; \
	git commit -m "New version $$NEW_VER"; \
	git tag "$$NEW_VER"; \
	autoconf --force
