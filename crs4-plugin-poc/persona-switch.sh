#!/bin/sh
set -eu

APP_PERSONA=${1:-}
WEB_PERSONA=${2:-}

if [ -z "$APP_PERSONA" ]; then
    echo "usage: persona-switch.sh <app-persona> [web-persona]" >&2
    exit 1
fi

case "$APP_PERSONA" in
    wordpress)
        BACKEND="http://persona_wordpress:5000"
        DEFAULT_WEB="apache"
        ;;
    joomla)
        BACKEND="http://persona_joomla:5000"
        DEFAULT_WEB="nginx"
        ;;
    phpmyadmin)
        BACKEND="http://persona_phpmyadmin:5000"
        DEFAULT_WEB="iis"
        ;;
    *)
        echo "unsupported app persona: $APP_PERSONA" >&2
        exit 1
        ;;
esac

if [ -z "$WEB_PERSONA" ]; then
    WEB_PERSONA="$DEFAULT_WEB"
fi

if [ ! -f "/etc/honeypot/personas/${WEB_PERSONA}.conf" ]; then
    echo "unsupported web persona: $WEB_PERSONA" >&2
    exit 1
fi

PERSONA_CONF=/usr/local/apache2/conf/extra/httpd-persona.conf
UPSTREAM_CONF=/usr/local/apache2/conf/extra/honeypot-upstream.conf

# Save originals for rollback
cp "$PERSONA_CONF" "${PERSONA_CONF}.bak" 2>/dev/null || true
cp "$UPSTREAM_CONF" "${UPSTREAM_CONF}.bak" 2>/dev/null || true

cp "/etc/honeypot/personas/${WEB_PERSONA}.conf" "$PERSONA_CONF"

cat > "$UPSTREAM_CONF" <<EOF
ProxyPass / ${BACKEND}/ retry=0 connectiontimeout=5 timeout=30
ProxyPassReverse / ${BACKEND}/
EOF

echo "[persona-switch] app=${APP_PERSONA} web=${WEB_PERSONA}" >&2

if apachectl configtest >/dev/null 2>&1; then
    apachectl -k graceful >/dev/null 2>&1 || true
    echo "$APP_PERSONA" > /tmp/active-app-persona
    rm -f "${PERSONA_CONF}.bak" "${UPSTREAM_CONF}.bak"
else
    echo "[persona-switch] configtest failed, rolling back" >&2
    cp "${PERSONA_CONF}.bak" "$PERSONA_CONF" 2>/dev/null || true
    cp "${UPSTREAM_CONF}.bak" "$UPSTREAM_CONF" 2>/dev/null || true
    rm -f "${PERSONA_CONF}.bak" "${UPSTREAM_CONF}.bak"
    exit 1
fi
