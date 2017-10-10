FROM fedora:26
MAINTAINER mmarusak@redhat.com

ARG password

RUN dnf -y update && \
    dnf install -y dnf-plugins-core && \
    dnf -y copr enable @abrt/faf-el7 && \
    dnf -y install git \
                   sudo \
                   which \
                   cronie \
                   postgresql-server \
                   postgresql \
                   python-psycopg2 \
                   pg-semver \
                   faf-* && \
    dnf clean all && \
    echo faf:${password:-passwd} | chpasswd && \
    echo 'faf ALL=(ALL:ALL) NOPASSWD:ALL' >> /etc/sudoers && \
    echo 'root ALL=(ALL:ALL) NOPASSWD:ALL' >> /etc/sudoers

# Copy initialization script
COPY docker/files/init_db /usr/bin

# Create crontabs and configurate FAF
ADD docker/files/crontab-faf /etc/faf/crontab-faf
RUN crontab -u faf /etc/faf/crontab-faf && \
    sed -i -e"s/CreateComponents\s*=\s*False/CreateComponents = True/i" /etc/faf/faf.conf && \
    sed -i -e"s/type\s*=\s*simple/type = null/i" /etc/faf/plugins/web.conf

VOLUME /var/lib/postgres
VOLUME /var/spool/faf

EXPOSE 80
CMD ["sh", "-c", "crond && init_db && apachectl -D FOREGROUND"]
