#!/bin/sh
set -eu

MODE=${1:-}
ACTION=${2:-}

case "$MODE" in
    rotation)
        SCRIPT="/opt/honeypot/persona-rotation.sh"
        PIDFILE="/tmp/persona-rotation.pid"
        ;;
    stimulus)
        SCRIPT="/opt/honeypot/persona-stimulus.sh"
        PIDFILE="/tmp/persona-stimulus.pid"
        ;;
    *)
        echo "unsupported mode: $MODE" >&2
        exit 2
        ;;
esac

is_running() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE" 2>/dev/null || true)
        if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

case "$ACTION" in
    start)
        if is_running; then
            echo "already-running"
            exit 0
        fi
        "$SCRIPT" >> /proc/1/fd/2 2>&1 &
        echo $! > "$PIDFILE"
        echo "started"
        ;;
    stop)
        if is_running; then
            PID=$(cat "$PIDFILE")
            kill "$PID" 2>/dev/null || true
            rm -f "$PIDFILE"
            echo "stopped"
        else
            rm -f "$PIDFILE"
            echo "already-stopped"
        fi
        ;;
    status)
        if is_running; then
            echo "running"
        else
            echo "stopped"
        fi
        ;;
    *)
        echo "unsupported action: $ACTION" >&2
        exit 2
        ;;
esac
