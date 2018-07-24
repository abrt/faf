repos_PYTHON = \
    __init__.py \
    rpm_metadata.py

if USE_DNF
    repos_PYTHON += dnf.py
endif

if USE_YUM
    repos_PYTHON += yum.py
endif

EXTRA_DIST = $(repos_PYTHON)

am__repos_PYTHON_DIST = $(repos_PYTHON)

reposdir = $(pythondir)/pyfaf/repos
