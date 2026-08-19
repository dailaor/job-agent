from __future__ import annotations

import asyncio
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .service import AgentService


class ApiHandler(BaseHTTPRequestHandler):
    service: AgentService
    static_dir = Path(__file__).with_name("static")

    def log_message(self, format: str, *args: object) -> None:
        print(f"[web] {self.address_string()} - {format % args}")

    def _json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 16 * 1024 * 1024:
            raise ValueError("请求内容过大")
        return json.loads(self.rfile.read(length) or b"{}")

    def _static(self, relative: str) -> None:
        relative = relative.lstrip("/") or "index.html"
        target = (self.static_dir / relative).resolve()
        if self.static_dir.resolve() not in target.parents and target != self.static_dir.resolve():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not target.is_file():
            target = self.static_dir / "index.html"
        body = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type + ("; charset=utf-8" if content_type.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/dashboard":
                self._json(self.service.dashboard())
            elif path == "/api/jobs":
                self._json(self.service.jobs())
            elif path == "/api/applications":
                self._json(self.service.applications())
            elif path == "/api/events":
                self._json(self.service.events())
            elif path == "/api/config":
                self._json(self.service.get_config())
            elif path == "/api/resume":
                self._json(self.service.resume_info())
            elif path == "/api/channels":
                self._json(self.service.channels())
            elif path.startswith("/api/"):
                self._json({"error": "not_found"}, 404)
            else:
                self._static(path)
        except Exception as exc:
            self._json({"error": type(exc).__name__, "message": str(exc)}, 500)

    def do_PUT(self) -> None:
        try:
            if urlparse(self.path).path == "/api/config":
                self._json(self.service.update_config(self._body()))
            else:
                self._json({"error": "not_found"}, 404)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self._json({"error": type(exc).__name__, "message": str(exc)}, 400)
        except Exception as exc:
            self._json({"error": type(exc).__name__, "message": str(exc)}, 500)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self._body()
            if path == "/api/resume":
                result = self.service.replace_resume(str(body["filename"]), str(body["content_base64"]))
                self._json(result)
                return
            agent = self.service.agent()
            if path == "/api/demo/seed":
                result = agent.seed_demo()
            elif path == "/api/run/discover":
                selected = body.get("channels")
                if isinstance(selected, list):
                    result = asyncio.run(agent.discover_selected([str(item) for item in selected]))
                else:
                    result = asyncio.run(agent.discover(str(body.get("channel", "all"))))
            elif path == "/api/run/evaluate":
                result = agent.evaluate()
            elif path == "/api/run/plan":
                result = agent.plan(str(body["channel"]))
            elif path == "/api/run/plan-all":
                result = agent.plan_all()
            elif path == "/api/run/execute":
                result = asyncio.run(agent.execute(str(body["channel"]), live=body.get("live") is True))
            elif path == "/api/run/execute-all":
                result = asyncio.run(agent.execute_all(live=body.get("live") is True))
            elif path == "/api/run/replies":
                result = asyncio.run(agent.check_boss_replies(live_resume_send=body.get("send_resume") is True))
            elif path == "/api/run/receipts":
                result = agent.check_receipts()
            elif path == "/api/run/cycle":
                result = asyncio.run(agent.run_cycle(live=body.get("live") is True))
            elif path == "/api/run/send-resume":
                result = asyncio.run(agent.send_boss_resume(int(body["application_id"]), live=body.get("live") is True))
            else:
                self._json({"error": "not_found"}, 404)
                return
            self._json(result)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self._json({"error": type(exc).__name__, "message": str(exc)}, 400)
        except Exception as exc:
            self._json({"error": type(exc).__name__, "message": str(exc)}, 500)


def serve(service: AgentService, host: str = "127.0.0.1", port: int = 8765) -> None:
    handler = type("ConfiguredApiHandler", (ApiHandler,), {"service": service})
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Job Agent dashboard: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
