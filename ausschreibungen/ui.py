"""Lokale Browseroberfläche für den bestehenden Berichtslauf."""

import errno
import hashlib
import json
import threading
import webbrowser
from dataclasses import asdict
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any
from urllib.parse import quote, unquote
from urllib.request import urlopen

from main import generate_report

from .analysis import load_analysis_profile, parse_analysis_profile
from .ted import load_profile, parse_profile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).with_name("ui_assets")
SETTINGS = ".ui-profile.json"
PORT = 8765


def validate_settings(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or not all(
        isinstance(data.get(k), dict) for k in ("search", "analysis")
    ):
        raise ValueError("Suchprofil und Unternehmensprofil werden benötigt.")
    return {
        "search": asdict(parse_profile(data["search"])),
        "analysis": parse_analysis_profile(data["analysis"]),
    }


def read_settings(root: Path) -> dict[str, Any]:
    path = root / SETTINGS
    if path.exists():
        return validate_settings(json.loads(path.read_text("utf-8")))
    return {
        "search": asdict(load_profile(root / "search-profile.toml")),
        "analysis": load_analysis_profile(root / "analysis-profile.toml"),
    }


def write_run_profiles(directory: Path, settings: dict[str, Any]) -> tuple[Path, Path]:
    # Die geprüften Profile enthalten ausschließlich Texte, ganze Zahlen und Listen.
    def value(item: Any) -> str:
        return json.dumps(item, ensure_ascii=False).replace("\x7f", "\\u007f")

    search = settings["search"]
    lines = [f"{key} = {value(item)}" for key, item in search.items() if key != "queries"]
    for query in search["queries"]:
        lines.extend(
            [
                "",
                "[[queries]]",
                f"name = {value(query['name'])}",
                f"term_groups = {value(query['term_groups'])}",
            ]
        )
    profile = directory / "search-profile.toml"
    profile.write_text("\n".join(lines) + "\n", "utf-8")
    analysis = directory / "analysis-profile.toml"
    analysis.write_text(
        "".join(f"{key} = {value(item)}\n" for key, item in settings["analysis"].items()), "utf-8"
    )
    return profile, analysis


class Busy(ValueError):
    """Der Browser zeigt einen älteren Stand oder es läuft bereits eine Recherche."""


class Application:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.lock = threading.Lock()
        self.status = "idle"
        self.messages: list[str] = []
        self.pdf: str | None = None
        self.analysis_progress: dict[str, int] | None = None

    def state(self) -> dict[str, Any]:
        with self.lock:
            return {
                "status": self.status,
                "messages": self.messages.copy(),
                "pdf": self.pdf,
                "analysis_progress": self.analysis_progress,
            }

    def submit(self, data: dict[str, Any], *, start: bool) -> None:
        with self.lock:
            if self.status == "running":
                raise Busy("Ein Bericht wird bereits erstellt.")
            if data.get("base") != read_settings(self.root):
                raise Busy("Das Profil hat sich geändert. Bitte lade die Seite neu.")
            if start:
                settings = validate_settings(data["base"])
                self.messages = []
                self.pdf = None
                self.analysis_progress = None
                self.status = "running"
                try:
                    threading.Thread(target=self.run, args=(settings,), daemon=True).start()
                except RuntimeError:
                    self.status = "failed"
                    raise
            else:
                settings = validate_settings(data.get("settings"))
                with NamedTemporaryFile(dir=self.root, suffix=".tmp", delete=False) as temp:
                    path = Path(temp.name)
                try:
                    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), "utf-8")
                    path.replace(self.root / SETTINGS)
                finally:
                    path.unlink(missing_ok=True)

    def message(self, text: str) -> None:
        with self.lock:
            self.messages.append(text)

    def update_analysis_progress(self, processed: int, total: int) -> None:
        with self.lock:
            self.analysis_progress = {"processed": processed, "total": total}

    def run(self, settings: dict[str, Any]) -> None:
        try:
            with TemporaryDirectory() as temp:
                search, analysis = write_run_profiles(Path(temp), settings)
                pdf, incomplete = generate_report(
                    search,
                    analysis,
                    self.root / "reports" / "ted-results.json",
                    self.message,
                    self.message,
                    on_analysis_progress=self.update_analysis_progress,
                )
            link = "/runs/" + quote(pdf.relative_to(self.root / "reports" / "runs").as_posix())
            with self.lock:
                self.pdf = link
                self.status = "incomplete" if incomplete else "complete"
        except Exception as exc:
            with self.lock:
                self.messages.append(f"Bericht konnte nicht erstellt werden: {exc}")
                self.status = "failed"


class Handler(BaseHTTPRequestHandler):
    def __init__(self, app: Application, *args: Any) -> None:
        self.app = app
        super().__init__(*args)

    @property
    def authority(self) -> str:
        return f"127.0.0.1:{self.server.server_address[1]}"

    def send(self, content: bytes, mime: str, code: int = 200, *, archive: bool = False) -> None:
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        policy = "default-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        if archive and mime != "application/pdf":
            policy = "sandbox allow-popups; default-src 'none'; style-src 'unsafe-inline'"
        self.send_header("Content-Security-Policy", policy)
        self.end_headers()
        self.wfile.write(content)

    def reply(self, data: Any, code: int = 200) -> None:
        self.send(json.dumps(data, ensure_ascii=False).encode(), "application/json", code)

    def do_GET(self) -> None:
        if self.headers.get("Host") != self.authority:
            self.send_error(403)
            return
        assets = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/app.css": ("app.css", "text/css; charset=utf-8"),
        }
        try:
            if self.path in assets:
                filename, mime = assets[self.path]
                self.send((ASSETS / filename).read_bytes(), mime)
            elif self.path == "/api/settings":
                self.reply(read_settings(self.app.root))
            elif self.path == "/api/status":
                self.reply(self.app.state())
            elif self.path == "/api/instance":
                self.reply(instance_id(self.app.root))
            elif self.path.startswith("/runs/"):
                self.archive_file(unquote(self.path[6:]))
            else:
                self.send_error(404)
        except (OSError, ValueError) as exc:
            self.reply({"error": str(exc)}, 400)

    def archive_file(self, relative: str) -> None:
        if any(piece in {"", ".", ".."} for piece in relative.split("/")) or any(
            ch in relative for ch in (":", "\\", "\0")
        ):
            self.send_error(404)
            return
        runs = (self.app.root / "reports" / "runs").resolve()
        path = (runs / relative).resolve()
        types = {
            ".html": "text/html; charset=utf-8",
            ".pdf": "application/pdf",
            ".xml": "text/plain; charset=utf-8",
            ".json": "application/json",
            ".toml": "text/plain; charset=utf-8",
        }
        if path.is_relative_to(runs) and path.suffix in types and path.is_file():
            self.send(path.read_bytes(), types[path.suffix], archive=True)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if (
            self.headers.get("Host") != self.authority
            or self.headers.get("Origin") != f"http://{self.authority}"
            or self.headers.get_content_type() != "application/json"
        ):
            self.send_error(403)
            return
        if self.path not in {"/api/settings", "/api/report"}:
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 2_000_000:
                raise ValueError("Ungültige Größe des Profils.")
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError("Ungültiges Profil.")
            self.app.submit(data, start=self.path == "/api/report")
            self.reply({"ok": True})
        except Busy as exc:
            self.reply({"error": str(exc)}, HTTPStatus.CONFLICT)
        except (ValueError, OSError) as exc:
            self.reply({"error": str(exc)}, 400)

    def log_message(self, format: str, *args: Any) -> None:
        pass


def instance_id(root: Path) -> str:
    return hashlib.sha256(str(root.resolve()).casefold().encode()).hexdigest()


class LocalServer(ThreadingHTTPServer):
    allow_reuse_address = False
    allow_reuse_port = False


def serve() -> None:
    url = f"http://127.0.0.1:{PORT}"
    try:
        server = LocalServer(("127.0.0.1", PORT), partial(Handler, Application(ROOT)))
    except OSError as exc:
        if exc.errno not in {errno.EADDRINUSE, 10048}:
            raise
        try:
            with urlopen(f"{url}/api/instance", timeout=2) as response:
                matches = json.load(response) == instance_id(ROOT)
        except (ValueError, OSError):
            matches = False
        if not matches:
            raise SystemExit(
                f"Port {PORT} ist belegt. Bitte die andere Anwendung schließen."
            ) from exc
        webbrowser.open(url)
        return
    with server:
        print(
            f"Oberfläche: {url}\nDieses Fenster während der Recherche geöffnet lassen.", flush=True
        )
        webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    serve()
