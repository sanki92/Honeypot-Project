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
filebeat -e -c /etc/filebeat/filebeat.yml -d "publish" &

# Monitor Apache - exit if it dies so Docker can restart the container
while true; do
    sleep 10
    if ! apachectl -t -D DUMP_RUN_CFG >/dev/null 2>&1 && ! pgrep -x httpd >/dev/null 2>&1; then
        echo "[entrypoint] Apache is not running, exiting" >&2
        exit 1
    fi
done
