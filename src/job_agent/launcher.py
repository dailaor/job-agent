from __future__ import annotations

import os
import shutil
import socket
import sys
import threading
import webbrowser
from pathlib import Path

from job_agent.service import AgentService
from job_agent.web import serve


def _application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _template_path(application_dir: Path) -> Path:
    bundled = Path(getattr(sys, "_MEIPASS", application_dir)) / "config.example.json"
    return bundled if bundled.is_file() else application_dir / "config.example.json"


def _available_port(preferred: int = 8765) -> int:
    for port in range(preferred, preferred + 10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("本机 8765-8774 端口均被占用，无法启动 Job Agent")


def main() -> None:
    application_dir = _application_dir()
    data_dir = application_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    config_path = data_dir / "config.json"
    if not config_path.exists():
        template = _template_path(application_dir)
        if not template.is_file():
            raise FileNotFoundError("安装包缺少 config.example.json")
        shutil.copyfile(template, config_path)
    port = _available_port()
    url = f"http://127.0.0.1:{port}"
    if os.environ.get("JOB_AGENT_NO_BROWSER") != "1":
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    serve(AgentService(config_path, data_dir / "job-agent.sqlite3"), port=port)


if __name__ == "__main__":
    main()
