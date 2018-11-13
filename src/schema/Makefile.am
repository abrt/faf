EXTRA_DIST = \
    faf_schema \
    README \
    setup.cfg \
    setup.py

all:

all-local:
	$(PYTHON) setup.py build --verbose

install-exec-local:
	$(PYTHON) setup.py install --root $(DESTDIR) \
		--single-version-externally-managed \
		--verbose
