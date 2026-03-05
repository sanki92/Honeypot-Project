FROM owasp/modsecurity-crs:apache

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget curl python3-watchdog && \
    rm -rf /var/lib/apt/lists/*

RUN wget -q https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-8.9.0-amd64.deb && \
    dpkg -i filebeat-8.9.0-amd64.deb && \
    rm filebeat-8.9.0-amd64.deb
COPY filebeat.yml /etc/filebeat/filebeat.yml
RUN chmod go-w /etc/filebeat/filebeat.yml

COPY plugins/honeytrap-config.conf /etc/modsecurity.d/owasp-crs/plugins/
COPY plugins/honeytrap-before.conf /etc/modsecurity.d/owasp-crs/plugins/
COPY plugins/honeytrap-after.conf  /etc/modsecurity.d/owasp-crs/plugins/

COPY include.conf /etc/modsecurity.d/
COPY modsecurity-override.conf /etc/modsecurity.d/

COPY httpd-honeypot.conf /usr/local/apache2/conf/extra/httpd-honeypot.conf
RUN echo 'Include conf/extra/httpd-honeypot.conf' >> /usr/local/apache2/conf/httpd.conf

COPY robots.txt  /usr/local/apache2/htdocs/
COPY index.html  /usr/local/apache2/htdocs/
COPY login.html  /usr/local/apache2/htdocs/

COPY preprocess-modsec-log.py /app/preprocess-modsec-log.py
RUN touch /var/log/modsec_audit_processed.log

RUN mkdir -p /tmp/modsecurity-data && chown www-data:www-data /tmp/modsecurity-data

RUN echo '' > /usr/local/apache2/conf/extra/httpd-proxy.conf
COPY httpd-vhosts.conf /usr/local/apache2/conf/extra/httpd-vhosts.conf

COPY personas/ /etc/honeypot/personas/
RUN echo 'ServerTokens Full' > /usr/local/apache2/conf/extra/httpd-persona.conf

COPY plugin-watcher.sh /opt/honeypot/plugin-watcher.sh
RUN chmod +x /opt/honeypot/plugin-watcher.sh

COPY modsec_entry.sh /modsec_entry.sh
RUN chmod +x /modsec_entry.sh

EXPOSE 80/tcp 8080/tcp 8000/tcp 8888/tcp

CMD ["/modsec_entry.sh"]
