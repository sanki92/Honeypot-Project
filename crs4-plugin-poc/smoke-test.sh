#!/bin/sh

set -eu

TOKEN=${1:-shanky}
HOST=${HOST:-localhost}
PASS=0
FAIL=0

check() {
    DESC=$1
    shift
    if OUTPUT=$("$@" 2>&1); then
        echo "  PASS: $DESC"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $DESC"
        echo "        $OUTPUT"
        FAIL=$((FAIL + 1))
    fi
}

expect_status() {
    URL=$1
    EXPECTED=$2
    HEADERS=${3:-}
    if [ -n "$HEADERS" ]; then
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "$HEADERS" "$URL")
    else
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL")
    fi
    [ "$STATUS" = "$EXPECTED" ]
}

expect_body_contains() {
    URL=$1
    PATTERN=$2
    HEADERS=${3:-}
    if [ -n "$HEADERS" ]; then
        BODY=$(curl -s -H "$HEADERS" "$URL")
    else
        BODY=$(curl -s "$URL")
    fi
    echo "$BODY" | grep -q "$PATTERN"
}

echo "=== Honeypot PoC Smoke Tests ==="
echo ""

echo "[Web endpoints]"
check "Main page returns 200" expect_status "http://${HOST}:9091/" "200"
check "Decoy port 8000 returns 403" expect_status "http://${HOST}:8000/" "403"
check "robots.txt returns 200" expect_status "http://${HOST}:9091/robots.txt" "200"
check "robots.txt contains Disallow bait" expect_body_contains "http://${HOST}:9091/robots.txt" "Disallow.*db_backup"
check "login.html returns 200" expect_status "http://${HOST}:9091/login.html" "200"
check "login.html contains hidden debug field" expect_body_contains "http://${HOST}:9091/login.html" "name=\"debug\""
check "Fake backup path returns 401" expect_status "http://${HOST}:9091/login.php.bak" "403"

echo ""
echo "[Control API]"
check "Health endpoint (no auth)" expect_status "http://${HOST}:9081/api/health" "200"
check "Status requires auth" expect_status "http://${HOST}:9081/api/status" "401"
check "Status with auth returns 200" expect_status "http://${HOST}:9081/api/status" "200" "X-API-Token: ${TOKEN}"
check "Status contains app persona" expect_body_contains "http://${HOST}:9081/api/status" "active_app_persona" "X-API-Token: ${TOKEN}"

echo ""
echo "[Persona app backends]"
check "WordPress persona responds" expect_body_contains "http://${HOST}:9091/" "WordPress\|wordpress"
check "wp-login.php returns 200" expect_status "http://${HOST}:9091/wp-login.php" "200"

echo ""
echo "=== Results: ${PASS} passed, ${FAIL} failed ==="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
