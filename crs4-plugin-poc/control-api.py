#!/usr/bin/python3
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = os.getenv("CONTROL_API_HOST", "0.0.0.0")
PORT = int(os.getenv("CONTROL_API_PORT", "8081"))
TOKEN = os.getenv("CONTROL_API_TOKEN", "shanky")

PLUGIN_CONFIG = Path("/etc/modsecurity.d/owasp-crs/plugins/honeytrap-config.conf")
PERSONA_FILE = Path("/usr/local/apache2/conf/extra/httpd-persona.conf")
ACTIVE_APP_FILE = Path("/tmp/active-app-persona")
API_LOG = Path("/var/log/control-api.log")

DISABLE_RULE = "SecAction \"id:9599010,phase:1,pass,nolog,setvar:'tx.honeytrap-plugin_enabled=0'\""
DISABLE_RULE_COMMENT = f"# {DISABLE_RULE}"

VALID_APP_PERSONAS = {"wordpress", "joomla", "phpmyadmin"}
VALID_WEB_PERSONAS = {"apache", "nginx", "iis"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_cmd(args):
    proc = subprocess.run(args, text=True, capture_output=True)
    return {
        "ok": proc.returncode == 0,
        "code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def log_action(action: str, detail: dict):
    API_LOG.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts": now_iso(), "action": action, "detail": detail}
    with API_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


def get_active_app_persona() -> str:
    if ACTIVE_APP_FILE.exists():
        return ACTIVE_APP_FILE.read_text(encoding="utf-8").strip() or "unknown"
    return "unknown"


def get_active_web_persona() -> str:
    if not PERSONA_FILE.exists():
        return "unknown"
    data = PERSONA_FILE.read_text(encoding="utf-8", errors="ignore")
    if "Microsoft-IIS/10.0" in data:
        return "iis"
    if "nginx/1.24.0" in data:
        return "nginx"
    if "Server \"Apache\"" in data:
        return "apache"
    return "unknown"


def plugin_enabled() -> bool:
    if not PLUGIN_CONFIG.exists():
        return True
    data = PLUGIN_CONFIG.read_text(encoding="utf-8", errors="ignore")
    for line in data.splitlines():
        stripped = line.strip()
        if stripped == DISABLE_RULE:
            return False
        if stripped == DISABLE_RULE_COMMENT:
            return True
    return True


def set_plugin_enabled(enabled: bool):
    if not PLUGIN_CONFIG.exists():
        return False, "plugin config not found"

    original = PLUGIN_CONFIG.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    updated_lines = []
    found = False

    for line in lines:
        line_ending = "\n"
        if line.endswith("\r\n"):
            line_ending = "\r\n"
        elif line.endswith("\n"):
            line_ending = "\n"
        else:
            line_ending = ""

        content = line[:-len(line_ending)] if line_ending else line
        stripped = content.strip()
        indent = content[: len(content) - len(content.lstrip())]

        if stripped == DISABLE_RULE or stripped == DISABLE_RULE_COMMENT:
            found = True
            if enabled:
                updated_lines.append(f"{indent}{DISABLE_RULE_COMMENT}{line_ending}")
            else:
                updated_lines.append(f"{indent}{DISABLE_RULE}{line_ending}")
        else:
            updated_lines.append(line)

    if not found:
        if updated_lines and not updated_lines[-1].endswith("\n"):
            updated_lines[-1] = updated_lines[-1] + "\n"
        rule_line = DISABLE_RULE_COMMENT if enabled else DISABLE_RULE
        updated_lines.append(rule_line + "\n")

    updated = "".join(updated_lines)

    if updated == original:
        return True, "no-change"

    PLUGIN_CONFIG.write_text(updated, encoding="utf-8")

    test = run_cmd(["apachectl", "configtest"])
    if not test["ok"]:
        PLUGIN_CONFIG.write_text(original, encoding="utf-8")
        return False, test["stderr"] or test["stdout"] or "configtest failed"

    reload_res = run_cmd(["apachectl", "-k", "graceful"])
    if not reload_res["ok"]:
        PLUGIN_CONFIG.write_text(original, encoding="utf-8")
        return False, reload_res["stderr"] or reload_res["stdout"] or "graceful failed"

    return True, "updated"


def switch_persona(app_persona: str, web_persona: str | None):
    cmd = ["/opt/honeypot/persona-switch.sh", app_persona]
    if web_persona:
        cmd.append(web_persona)
    result = run_cmd(cmd)
    if result["ok"]:
        return True, "switched"
    return False, result["stderr"] or result["stdout"] or "switch failed"


def set_mode(mode: str, enabled: bool):
    action = "start" if enabled else "stop"
    result = run_cmd(["/opt/honeypot/persona-mode.sh", mode, action])
    if not result["ok"]:
        return False, result["stderr"] or result["stdout"] or "mode action failed"
    return True, result["stdout"] or action


def mode_status(mode: str) -> str:
    result = run_cmd(["/opt/honeypot/persona-mode.sh", mode, "status"])
    if result["ok"] and result["stdout"] in ("running", "stopped"):
        return result["stdout"]
    return "unknown"


def reload_apache():
    test = run_cmd(["apachectl", "configtest"])
    if not test["ok"]:
        return False, test["stderr"] or test["stdout"] or "configtest failed"
    reload_res = run_cmd(["apachectl", "-k", "graceful"])
    if not reload_res["ok"]:
        return False, reload_res["stderr"] or reload_res["stdout"] or "graceful failed"
    return True, "reloaded"


class Handler(BaseHTTPRequestHandler):
    server_version = "honeypot-control-api"

    def _json(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _parse_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _authorized(self) -> bool:
        if TOKEN == "":
            return True
        header_token = self.headers.get("X-API-Token", "")
        if header_token == TOKEN:
            return True
        auth = self.headers.get("Authorization", "")
        if auth.lower().startswith("bearer ") and auth[7:] == TOKEN:
            return True
        return False

    def _require_auth(self):
        if self._authorized():
            return True
        self._json(401, {"ok": False, "error": "unauthorized"})
        return False

    def do_GET(self):
        if self.path == "/api/health":
            self._json(200, {"ok": True, "status": "up", "ts": now_iso()})
            return

        if self.path == "/api/status":
            if not self._require_auth():
                return
            payload = {
                "ok": True,
                "active_app_persona": get_active_app_persona(),
                "active_web_persona": get_active_web_persona(),
                "plugin_enabled": plugin_enabled(),
                "rotation_mode": mode_status("rotation"),
                "stimulus_mode": mode_status("stimulus"),
            }
            self._json(200, payload)
            return

        self._json(404, {"ok": False, "error": "not-found"})

    def do_POST(self):
        if not self._require_auth():
            return

        try:
            body = self._parse_body()
        except Exception:
            self._json(400, {"ok": False, "error": "invalid-json"})
            return

        if self.path == "/api/reload":
            ok, msg = reload_apache()
            log_action("reload", {"ok": ok, "msg": msg})
            self._json(200 if ok else 400, {"ok": ok, "message": msg})
            return

        if self.path == "/api/plugin/toggle":
            enabled = body.get("enabled")
            if not isinstance(enabled, bool):
                self._json(400, {"ok": False, "error": "enabled must be boolean"})
                return
            ok, msg = set_plugin_enabled(enabled)
            log_action("plugin-toggle", {"ok": ok, "enabled": enabled, "msg": msg})
            self._json(200 if ok else 400, {"ok": ok, "message": msg, "enabled": enabled})
            return

        if self.path == "/api/persona/switch":
            app_persona = body.get("app_persona", "")
            web_persona = body.get("web_persona")
            if not isinstance(app_persona, str) or app_persona == "":
                self._json(400, {"ok": False, "error": "app_persona is required"})
                return
            if app_persona not in VALID_APP_PERSONAS:
                self._json(400, {"ok": False, "error": f"app_persona must be one of {sorted(VALID_APP_PERSONAS)}"})
                return
            if web_persona is not None:
                if not isinstance(web_persona, str):
                    self._json(400, {"ok": False, "error": "web_persona must be string"})
                    return
                if web_persona not in VALID_WEB_PERSONAS:
                    self._json(400, {"ok": False, "error": f"web_persona must be one of {sorted(VALID_WEB_PERSONAS)}"})
                    return
            ok, msg = switch_persona(app_persona, web_persona)
            log_action("persona-switch", {"ok": ok, "app": app_persona, "web": web_persona, "msg": msg})
            self._json(200 if ok else 400, {"ok": ok, "message": msg})
            return

        if self.path == "/api/modes":
            rotation = body.get("rotation_enabled")
            stimulus = body.get("stimulus_enabled")
            results = {}

            if rotation is not None:
                if not isinstance(rotation, bool):
                    self._json(400, {"ok": False, "error": "rotation_enabled must be boolean"})
                    return
                ok, msg = set_mode("rotation", rotation)
                results["rotation"] = {"ok": ok, "message": msg, "enabled": rotation}

            if stimulus is not None:
                if not isinstance(stimulus, bool):
                    self._json(400, {"ok": False, "error": "stimulus_enabled must be boolean"})
                    return
                ok, msg = set_mode("stimulus", stimulus)
                results["stimulus"] = {"ok": ok, "message": msg, "enabled": stimulus}

            if not results:
                self._json(400, {"ok": False, "error": "no mode field provided"})
                return

            overall_ok = all(v["ok"] for v in results.values())
            log_action("modes", {"ok": overall_ok, "results": results})
            self._json(200 if overall_ok else 400, {"ok": overall_ok, "results": results})
            return

        self._json(404, {"ok": False, "error": "not-found"})


def main():
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[control-api] listening on {HOST}:{PORT}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
