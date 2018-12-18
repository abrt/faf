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
  about.md \
  base.html \
  rstpage.html

templatedir = $(pythondir)/webfaf/templates

# Use README.md from project root
about.md: about.md.in
	cp ../../../README.md about.md

EXTRA_DIST = $(template_DATA) about.md.in
