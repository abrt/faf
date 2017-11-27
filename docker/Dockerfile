FROM fedora:26
MAINTAINER mmarusak@redhat.com

ARG password

RUN dnf -y update && \
    dnf install -y dnf-plugins-core && \
    dnf -y copr enable @abrt/faf-el7 && \
    dnf -y install git \
                   sudo \
                   which \
                   uwsgi \
                   postgresql \
                   pg-semver \
                   python-psycopg2 \
                   faf-* && \
    dnf clean all && \
    echo faf:${password:-passwd} | chpasswd && \
    echo 'faf ALL=(ALL:ALL) NOPASSWD:ALL' >> /etc/sudoers && \
    echo 'root ALL=(ALL:ALL) NOPASSWD:ALL' >> /etc/sudoers

# Copy main run script
COPY docker/files/run_faf /usr/bin

RUN sed -i -e"s/CreateComponents\s*=\s*False/CreateComponents = True/i" /etc/faf/faf.conf && \
    sed -i -e"s/type\s*=\s*simple/type = null/i" /etc/faf/plugins/web.conf && \
    echo "cron = -5 -1 -1 -1 -1 faf save-reports -v" >> /etc/uwsgi.ini && \
    echo "cron =  0 -5 -1 -1 -1 faf create-problems" >> /etc/uwsgi.ini && \
    chown faf:faf /run/uwsgi/

VOLUME /var/spool/faf

EXPOSE 80
CMD ["sh", "-c", "run_faf"]
