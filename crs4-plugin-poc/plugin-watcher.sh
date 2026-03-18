#!/bin/sh
set -eu

PLUGIN_DIR=/etc/modsecurity.d/owasp-crs/plugins
HASH_FILE=/tmp/.plugin-hash

md5sum ${PLUGIN_DIR}/*.conf 2>/dev/null | sort > "$HASH_FILE"

while true; do
    sleep 5
    NEW_HASH=$(md5sum ${PLUGIN_DIR}/*.conf 2>/dev/null | sort)
    OLD_HASH=$(cat "$HASH_FILE" 2>/dev/null)
    if [ "$NEW_HASH" != "$OLD_HASH" ]; then
        echo "$NEW_HASH" > "$HASH_FILE"
        sleep 1
        if apachectl configtest 2>/dev/null; then
            apachectl -k graceful
            echo "[plugin-watcher] reloaded apache" >&2
        else
            echo "[plugin-watcher] configtest failed, skipping reload" >&2
        fi
    fi
done
