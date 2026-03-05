# Honeytrap- CRS 4 Plugin PoC

Migrates the five existing honeytrap deception rules from `modsecurity-extension.conf` into a proper CRS 4.x plugin (IDs 9,599,000–9,599,999), adds a hot-reload watcher, and swappable server personas for Shodan fingerprint spoofing.

## Quick start

```bash
docker compose up --build -d
docker exec modsec_honeypot apachectl configtest 
```

---

## Step 1: CRS 4 plugin migration

The original rules were appended directly to `modsecurity.conf` via shell. This moves them into the three-file CRS 4 plugin format that the plugin registry expects:

```
plugins/
├── honeytrap-config.conf   ← SecContentInjection, enable/disable toggle
├── honeytrap-before.conf   ← request-phase detection (traps 1–5)
└── honeytrap-after.conf    ← response-phase injection (traps 2–5)
```

**The five traps:**

- **Trap 1**: traffic on ports 8000/8888 → 403
- **Trap 2**: `robots.txt` gets a fake `Disallow: /db_backup.<epoch>` injected; following that path serves a 401 Basic Auth challenge and captures any submitted credentials
- **Trap 3**: `login.html` gets `<!-- DEBUG - old login page is login.php.bak -->` injected; requesting that file → 403
- **Trap 4**: every `<form>` gets a hidden `debug=false` field injected; flipping the value → 403
- **Trap 5**: any `Set-Cookie` response gets a piggybacked `<name>-user_role=Admin:0` cookie; tampering with it → 403

**Verify:**

```bash
curl -i http://localhost:9091/                      # 200
curl -i http://localhost:8000/                      # 403 trap 1
curl    http://localhost:9091/robots.txt            # Disallow: /db_backup.<epoch>
curl -i http://localhost:9091/db_backup.1234567890  # 401 + WWW-Authenticate
curl    http://localhost:9091/login.html | grep bak # injected HTML comment
curl -i http://localhost:9091/login.php.bak         # 403 trap 3

# live audit log
docker exec modsec_honeypot tail -f /var/log/modsec_audit.log
```

---

## Step 2: Plugin hot-reload

`plugin-watcher.sh` runs in the background and polls the plugins directory every 5 seconds using `md5sum`. When anything changes it runs `apachectl configtest` and if the config is valid, does a `graceful` restart. Bad configs are skipped and logged.

The `plugins/` directory is bind-mounted from the host, so editing a plugin `.conf` file locally is enough to trigger a reload, no container restart needed.

**Verify:**

```bash
# modify any plugin file (from inside the container or on the host)
docker exec modsec_honeypot sh -c "echo '# test' >> /etc/modsecurity.d/owasp-crs/plugins/honeytrap-config.conf"

docker logs modsec_honeypot 2>&1 | grep plugin-watcher
# → [plugin-watcher] reloaded apache

# apache is still serving
curl -i http://localhost:9091/  # still 200
```

---

## Step 3: Chameleon personas

Set `HONEYPOT_PERSONA` in `docker-compose.yml`. At startup, `modsec_entry.sh` copies the matching persona file into place, which sets `SecServerSignature`, extra headers, and custom error pages.

| Persona | `Server` | Extra headers | Error page style |
|---------|----------|---------------|-----------------|
| `apache` (default) | `Apache` | — | standard |
| `nginx` | `nginx/1.24.0` | `X-Powered-By: PHP/8.2.15` | nginx |
| `iis` | `Microsoft-IIS/10.0` | `X-Powered-By: ASP.NET`, `X-AspNet-Version: 4.0.30319` | IIS |

```yaml
environment:
  - HONEYPOT_PERSONA=nginx   # apache | nginx | iis
```

**Verify:**

```bash
# after docker compose up -d with HONEYPOT_PERSONA=nginx
curl -I http://localhost:9091/
curl http://localhost:8000/


# switch to iis: change HONEYPOT_PERSONA=iis in docker-compose.yml, then:
docker compose down && docker compose up -d
curl -I http://localhost:9091/
```

---

## Disabling the plugin

Uncomment in `plugins/honeytrap-config.conf`, then let the watcher pick it up (or run `apachectl -k graceful`):

```apache
SecAction "id:9599010,phase:1,pass,nolog,setvar:'tx.honeytrap-plugin_enabled=0'"
```

## What's next

- Step 4: REST API for runtime rule management

