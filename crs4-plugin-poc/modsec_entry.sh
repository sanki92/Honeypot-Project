#!/bin/sh
mkdir -p /tmp/modsecurity-data

PERSONA=${HONEYPOT_PERSONA:-apache}
cp /etc/honeypot/personas/${PERSONA}.conf /usr/local/apache2/conf/extra/httpd-persona.conf

apachectl
/opt/honeypot/plugin-watcher.sh &
python3 /app/preprocess-modsec-log.py &
filebeat -e -c /etc/filebeat/filebeat.yml -d "publish"
