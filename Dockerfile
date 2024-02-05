FROM quay.io/abrt/faf:2.5.0

USER root
RUN dnf install -y python3-jira python-requests-kerberos
USER faf

COPY src/pyfaf/bugtrackers/rheljira.py /usr/lib/python3.8/site-packages/pyfaf/bugtrackers/
COPY src/webfaf/reports.py /usr/lib/python3.8/site-packages/webfaf/reports.py
COPY src/pyfaf/storage/bugzilla.py /usr/lib/python3.8/site-packages/pyfaf/storage/bugzilla.py
