# Honeytrap CRS4 Adaptive PoC

This is the PoC I built for the OWASP Honeypot Project to make the ModSecurity setup adaptive instead of static.

I focused on four steps and implemented each one end-to-end.

## What I Built

1. Step 1: Migrated honeytrap logic into CRS4 plugin format
2. Step 2: Added safe hot-reload for plugin updates
3. Step 3: Added chameleon personas at server + application level
4. Step 4: Added a runtime control API for safe operations

## Project Structure

```text
crs4-plugin-poc/
  docker-compose.yml
  Dockerfile
  modsec_entry.sh
  plugin-watcher.sh
  control-api.py
  persona-switch.sh
  persona-rotation.sh
  persona-stimulus.sh
  persona-mode.sh
  httpd-vhosts.conf
  httpd-honeypot.conf
  include.conf
  modsecurity-override.conf
  preprocess-modsec-log.py
  filebeat.yml
  sample-env

  plugins/
    honeytrap-config.conf
    honeytrap-before.conf
    honeytrap-after.conf

  personas/
    apache.conf
    nginx.conf
    iis.conf

  persona-app/
    app.py
    Dockerfile
    requirements.txt

  logstash/
    pipeline/
      logstash.conf
```

## Step-by-Step Implementation

### Step 1: CRS4 Plugin Migration

I moved trap rules into CRS4 plugin stages:

- plugins/honeytrap-config.conf
- plugins/honeytrap-before.conf
- plugins/honeytrap-after.conf

Implemented trap behavior:

- decoy port detection on 8000 and 8888
- robots bait path injection with timestamped fake backup URL
- fake auth challenge and credential-attempt capture
- fake backup hint injection in login page HTML
- hidden field tamper detection
- fake cookie tamper detection

### Step 2: Hot Reload

I added plugin-watcher.sh to watch plugin checksum changes.

On change it does:

1. apachectl configtest
2. apachectl -k graceful (only if configtest passes)

This avoids full restart loops and prevents applying broken config.

### Step 3: Chameleon Personas

I implemented persona switching at two layers:

- server signature layer via personas/apache.conf, personas/nginx.conf, personas/iis.conf
- application fingerprint layer via persona backends:
  - persona_wordpress
  - persona_joomla
  - persona_phpmyadmin

persona-switch.sh updates both upstream routing and web signature profile, then validates and applies config safely.

I also added mode scripts:

- persona-rotation.sh for timed switching
- persona-stimulus.sh for event-driven switching from trap signals
- persona-mode.sh for start/stop/status control

### Step 4: Runtime Control API

I added control-api.py (container port 8081, exposed as host port 9081) to expose operational controls without shell editing.

Authentication:

- X-API-Token header
- or Bearer token

Both methods are supported by the API. You can use either one.

API contract:

| Method | Path | Purpose | Request body |
|---|---|---|---|
| GET | /api/health | Health check | None |
| GET | /api/status | Active app/web persona, plugin state, mode state | None |
| POST | /api/reload | Config test + graceful reload | None |
| POST | /api/plugin/toggle | Enable or disable plugin | {"enabled": true} or {"enabled": false} |
| POST | /api/persona/switch | Switch app persona and optional web persona | {"app_persona":"wordpress"} or {"app_persona":"joomla","web_persona":"nginx"} |
| POST | /api/modes | Start or stop rotation/stimulus modes | {"rotation_enabled": true}, {"stimulus_enabled": false}, or both |

Valid values:

- app_persona: wordpress, joomla, phpmyadmin
- web_persona: apache, nginx, iis
- enabled, rotation_enabled, stimulus_enabled: true or false

Safety behavior I implemented:

- reload only after configtest passes
- plugin toggle rollback if apply fails
- action logging to /var/log/control-api.log

## Default Runtime Values

From docker-compose.yml:

- ACTIVE_APP_PERSONA=wordpress
- HONEYPOT_PERSONA=apache
- PERSONA_ROTATION_ENABLED=false
- PERSONA_ROTATION_INTERVAL=300
- PERSONA_ROTATION_LIST=wordpress,joomla,phpmyadmin
- PERSONA_STIMULI_ENABLED=false
- PERSONA_STIMULI_COOLDOWN=120
- CONTROL_API_TOKEN=shanky

## Run

```bash
docker compose up --build -d
docker exec modsec_honeypot apachectl configtest
```

## Quick Verification

```bash
curl -i http://localhost:9091/
curl -i http://localhost:8000/
curl -H "X-API-Token: shanky" http://localhost:9081/api/status
```

## Smoke Tests

```bash
./smoke-test.sh
```

Uses the default token (`shanky`). To override: `./smoke-test.sh <your-token>`

Runs automated checks against web endpoints, control API, and persona backends.