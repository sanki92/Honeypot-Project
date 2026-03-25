#!/bin/sh
set -eu

LOG_FILE=/var/log/modsec_audit.log
COOLDOWN=${PERSONA_STIMULI_COOLDOWN:-120}
LAST_SWITCH=0

if [ ! -f "$LOG_FILE" ]; then
    touch "$LOG_FILE"
fi

tail -Fn0 "$LOG_FILE" | while IFS= read -r line; do
    TARGET=""

    case "$line" in
        *"Fake HTML Comment Data Used"*) TARGET="joomla" ;;
        *"Hidden Form Field Manipulated"*) TARGET="phpmyadmin" ;;
        *"Fake Cookie Data Manipulation"*) TARGET="wordpress" ;;
    esac

    if [ -z "$TARGET" ]; then
        continue
    fi

    NOW=$(date +%s)
    if [ $((NOW - LAST_SWITCH)) -lt "$COOLDOWN" ]; then
        continue
    fi

    CURRENT=$(cat /tmp/active-app-persona 2>/dev/null || echo "")
    if [ "$CURRENT" = "$TARGET" ]; then
        continue
    fi

    if /opt/honeypot/persona-switch.sh "$TARGET"; then
        LAST_SWITCH=$NOW
        echo "[persona-stimulus] switched to $TARGET" >&2
    fi
done
