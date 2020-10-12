# Stage 1: Build RPMs

FROM fedora:32
USER root
RUN dnf --assumeyes install git-core make tito && \
    git clone --quiet https://github.com/abrt/faf.git /src && \
    dnf --assumeyes builddep --spec /src/faf.spec && \
    useradd --no-create-home builder && \
    chown --recursive --quiet builder:builder /src
USER builder
WORKDIR /src
RUN tito build --rpm

# Stage 2: Upgrade system and install FAF RPMs

FROM fedora:32 as build
USER root
COPY --from=0 /tmp/tito/noarch/faf-*.rpm /tmp/
RUN \
    dnf --assumeyes upgrade && \
    dnf --assumeyes install findutils uwsgi /tmp/faf-*.rpm && \
    dnf clean all

# Stage 3: Set up FAF

FROM build

ENV NAME="ABRT Analytics" \
    SUMMARY="ABRT Analytics - Collects and aggregate unhandled applications crashes." \
    DESCRIPTION="ABRT Analytics - Collects and aggregate unhandled applications crashes. \
ABRT Analytics now collects thousands of reports a day serving needs of three different projects \
 - CentOS \
 - Fedora \
 - Red Hat Enterprise Linux"

LABEL summary="$SUMMARY" \
      description="$DESCRIPTION" \
      io.openshift.tags="faf,crash,abrt,analytics" \
      io.k8s.description="$DESCRIPTION" \
      io.k8s.display-name="ABRT Analytics" \
      io.openshift.expose-services="8080:TCP" \
      name="$NAME" \
      usage="podman run -d --name faf -e PGUSER=faf PGPASSWORD=pass PGDATABASE=faf PGHOST=host PGPORT=5432" \
      maintainer="ABRT devel team <abrt-devel-list@redhat.com>"

# Copy main run script
COPY container/files/usr/bin/* /usr/bin/
COPY container/files/usr/libexec/* /usr/libexec/

RUN sed -i -e"s/CreateComponents\s*=\s*False/CreateComponents = True/i" /etc/faf/faf.conf && \
    sed -i -e"s/type\s*=\s*simple/type = null/i" /etc/faf/plugins/web.conf && \
    rm -rf /run/httpd && mkdir /run/httpd && chmod -R a+rwx /run/httpd && \
    sed -i -e"s/Listen\s*80/Listen 8080/i" /etc/httpd/conf/httpd.conf && \
    sed -i -e"s/ErrorLog\s*\"logs\/error_log\"/ErrorLog \"\/var\/log\/faf\/httpd_error_log\"/i" /etc/httpd/conf/httpd.conf && \
    sed -i -e"s/CustomLog\s*\"logs\/access_log\"/CustomLog \"\/var\/log\/faf\/httpd_access_log\"/i" /etc/httpd/conf/httpd.conf && \
    echo "cron = -5 -1 -1 -1 -1 faf save-reports" >> /etc/uwsgi.ini && \
    echo "cron =  0 -5 -1 -1 -1 faf create-problems" >> /etc/uwsgi.ini && \
    chmod g=u /etc/passwd && \
    mkdir -p /run/uwsgi && \
    /usr/libexec/fix-permissions /run/uwsgi && \
    /usr/libexec/fix-permissions /run/faf-celery && \
    /usr/libexec/fix-permissions /var/log/faf && \
    /usr/libexec/fix-permissions /var/spool/faf && \
    /usr/libexec/fix-permissions /etc/faf/

VOLUME /var/spool/faf

# Run the container as user faf
USER faf

EXPOSE 8080

ENTRYPOINT ["faf-entrypoint"]
CMD ["run_faf"]
