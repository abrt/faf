FROM fedora:27
MAINTAINER mmarusak@redhat.com

RUN dnf -y update && \
    dnf install -y dnf-plugins-core && \
    dnf -y copr enable @abrt/faf-el7 && \
    dnf -y install uwsgi \
                   findutils \
                   faf-* && \
    dnf clean all

# Copy main run script
COPY docker/files/usr/bin /usr/bin
COPY docker/files/usr/libexec /usr/libexec

RUN sed -i -e"s/CreateComponents\s*=\s*False/CreateComponents = True/i" /etc/faf/faf.conf && \
    sed -i -e"s/type\s*=\s*simple/type = null/i" /etc/faf/plugins/web.conf && \
    rm -rf /run/httpd && mkdir /run/httpd && chmod -R a+rwx /run/httpd && \
    sed -i -e"s/Listen\s*80/Listen 8080/i" /etc/httpd/conf/httpd.conf && \
    sed -i -e"s/ErrorLog\s*\"logs\/error_log\"/ErrorLog \"\/var\/log\/faf\/httpd_error_log\"/i" /etc/httpd/conf/httpd.conf && \
    sed -i -e"s/CustomLog\s*\"logs\/access_log\"/CustomLog \"\/var\/log\/faf\/httpd_access_log\"/i" /etc/httpd/conf/httpd.conf && \
    echo "cron = -5 -1 -1 -1 -1 faf save-reports -v" >> /etc/uwsgi.ini && \
    echo "cron =  0 -5 -1 -1 -1 faf create-problems" >> /etc/uwsgi.ini && \
    chmod g=u /etc/passwd && \
    /usr/libexec/fix-permissions /run/uwsgi && \
    /usr/libexec/fix-permissions /run/faf-celery && \
    /usr/libexec/fix-permissions /var/log/faf && \
    /usr/libexec/fix-permissions /var/spool/faf

VOLUME /var/spool/faf

# Run the container as user faf
USER 997

EXPOSE 8080

ENTRYPOINT ["faf-entrypoint"]
CMD ["run_faf"]
