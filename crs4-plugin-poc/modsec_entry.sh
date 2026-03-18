#!/bin/sh
set -eu

mkdir -p /tmp/modsecurity-data

ACTIVE_APP_PERSONA=${ACTIVE_APP_PERSONA:-wordpress}
HONEYPOT_PERSONA=${HONEYPOT_PERSONA:-}

/opt/honeypot/persona-switch.sh "$ACTIVE_APP_PERSONA" "$HONEYPOT_PERSONA"

apachectl

python3 /opt/honeypot/control-api.py &

/opt/honeypot/plugin-watcher.sh &

if [ "${PERSONA_ROTATION_ENABLED:-false}" = "true" ]; then
    /opt/honeypot/persona-mode.sh rotation start >/dev/null
fi

if [ "${PERSONA_STIMULI_ENABLED:-false}" = "true" ]; then
    /opt/honeypot/persona-mode.sh stimulus start >/dev/null
fi

python3 /app/preprocess-modsec-log.py &
filebeat -e -c /etc/filebeat/filebeat.yml -d "publish"
