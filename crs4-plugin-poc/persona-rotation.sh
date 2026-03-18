#!/bin/sh
set -eu

INTERVAL=${PERSONA_ROTATION_INTERVAL:-300}
LIST=${PERSONA_ROTATION_LIST:-wordpress,joomla,phpmyadmin}

while true; do
    sleep "$INTERVAL"

    CURRENT=$(cat /tmp/active-app-persona 2>/dev/null || echo "")
    NEXT=""

    OLD_IFS=$IFS
    IFS=','
    set -- $LIST
    IFS=$OLD_IFS

    FIRST=${1:-wordpress}
    PICK_NEXT=false
    for p in "$@"; do
        if [ "$PICK_NEXT" = true ]; then
            NEXT="$p"
            break
        fi
        if [ "$p" = "$CURRENT" ]; then
            PICK_NEXT=true
        fi
    done

    if [ -z "$NEXT" ]; then
        NEXT="$FIRST"
    fi

    /opt/honeypot/persona-switch.sh "$NEXT"
    echo "[persona-rotation] switched to $NEXT" >&2
done
