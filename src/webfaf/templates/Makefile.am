SUBDIRS = \
  celery_tasks \
  dumpdirs \
  problems \
  reports \
  stats \
  summary

template_DATA = \
  _helpers.html \
  403.html \
  404.html \
  413.html \
  500.html \
  about.rst \
  base.html \
  rstpage.html

templatedir = $(pythondir)/webfaf/templates

# Use README.rst from project root
about.rst: about.rst.in
	cp ../../../README.rst about.rst

EXTRA_DIST = $(template_DATA) about.rst.in
