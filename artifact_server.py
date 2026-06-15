#!/usr/bin/env python3
"""
Artifact Server — Simple HTTP server for downloading AI-generated artifacts.

Serves files from a configured artifacts directory with a clean web UI
that lists all files with download links.

_usage:_
    python artifact_server.py [--port PORT] [--dir DIR] [--host HOST] [--list] [--stop]

_examples:_
    # Start server on default port
    python artifact_server.py

    # Start on custom port and directory
    python artifact_server.py --port 8082 --dir /path/to/files

    # List running server PID
    python artifact_server.py --list

    # Stop running server
    python artifact_server.py --stop

_config:_
    Default port: 8082
    Default host: 0.0.0.0 (accessible on LAN)
    Default dir: ~/Documents/ai_workloads/artifacts/
    PID file: /tmp/artifact_server.pid
"""

import http.server
import socketserver
import argparse
import os
import sys
import json
import time
import signal
import threading
from pathlib import Path
from datetime import datetime
from urllib.parse import quote


DEFAULT_PORT = 8082
DEFAULT_HOST = "0.0.0.0"
DEFAULT_DIR = os.path.expanduser("~/Documents/ai_workloads/artifacts")
PID_FILE = "/tmp/artifact_server.pid"


def get_file_info(filepath):
    """Get file metadata for display."""
    stat = os.stat(filepath)
    size = stat.st_size
    mtime = stat.st_mtime

    if size < 1024:
        size_str = f"{size} B"
    elif size < 1024 * 1024:
        size_str = f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        size_str = f"{size / (1024 * 1024):.1f} MB"
    else:
        size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"

    modified = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

    ext = Path(filepath).suffix.lower()
    mime_types = {
        ".pdf": "application/pdf",
        ".html": "text/html",
        ".htm": "text/html",
        ".txt": "text/plain",
        ".md": "text/plain",
        ".csv": "text/csv",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".mp4": "video/mp4",
        ".zip": "application/zip",
        ".gz": "application/gzip",
        ".tar": "application/x-tar",
        ".py": "text/x-python",
        ".sh": "text/x-sh",
        ".yaml": "text/yaml",
        ".yml": "text/yaml",
        ".xml": "application/xml",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    return {
        "name": os.path.basename(filepath),
        "path": filepath,
        "size": size_str,
        "size_bytes": size,
        "modified": modified,
        "mime": mime_types.get(ext, "application/octet-stream"),
        "ext": ext,
    }


def get_icon_for_ext(ext):
    """Get a display icon/emoji for file type."""
    icons = {
        ".pdf": "PDF",
        ".html": "HTML",
        ".htm": "HTML",
        ".txt": "TXT",
        ".md": "MD",
        ".csv": "CSV",
        ".json": "JSON",
        ".png": "PNG",
        ".jpg": "JPG",
        ".jpeg": "JPG",
        ".gif": "GIF",
        ".svg": "SVG",
        ".mp4": "MP4",
        ".zip": "ZIP",
        ".gz": "GZ",
        ".tar": "TAR",
        ".py": "PY",
        ".sh": "SH",
        ".yaml": "YML",
        ".yml": "YML",
        ".xml": "XML",
        ".docx": "DOCX",
        ".xlsx": "XLSX",
    }
    return icons.get(ext, "FILE")


def get_color_for_ext(ext):
    """Get a color for the file type badge."""
    colors = {
        ".pdf": "#e74c3c",
        ".html": "#e67e22",
        ".htm": "#e67e22",
        ".txt": "#95a5a6",
        ".md": "#95a5a6",
        ".csv": "#27ae60",
        ".json": "#f39c12",
        ".png": "#8e44ad",
        ".jpg": "#8e44ad",
        ".jpeg": "#8e44ad",
        ".gif": "#8e44ad",
        ".svg": "#8e44ad",
        ".mp4": "#2980b9",
        ".zip": "#e67e22",
        ".gz": "#e67e22",
        ".tar": "#e67e22",
        ".py": "#3498db",
        ".sh": "#2ecc71",
        ".yaml": "#9b59b6",
        ".yml": "#9b59b6",
        ".xml": "#f39c12",
        ".docx": "#2980b9",
        ".xlsx": "#27ae60",
    }
    return colors.get(ext, "#7f8c8d")


class ArtifactHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler that serves artifacts with a nice UI."""

    artifacts_dir = DEFAULT_DIR

    def translate_path(self, path):
        """Override to serve from artifacts directory."""
        # For direct file requests, serve from artifacts dir
        if path.startswith("/download/"):
            filename = path[len("/download/"):]
            # Prevent directory traversal
            filename = os.path.basename(filename)
            return os.path.join(self.artifacts_dir, filename)
        return super().translate_path(path)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_index()
        elif self.path.startswith("/download/"):
            self.send_file()
        elif self.path == "/api/files":
            self.send_api()
        else:
            self.send_error(404, "Not found")

    def send_index(self):
        files = self.get_artifact_list()
        html = self.render_html(files)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode())))
        self.end_headers()
        self.wfile.write(html.encode())

    def send_file(self):
        try:
            filename = self.path[len("/download/"):]
            filename = os.path.basename(filename)
            filepath = os.path.join(self.artifacts_dir, filename)

            if not os.path.isfile(filepath):
                self.send_error(404, f"File not found: {filename}")
                return

            info = get_file_info(filepath)

            self.send_response(200)
            self.send_header("Content-Type", info["mime"])
            self.send_header("Content-Length", str(info["size_bytes"]))
            self.send_header("Content-Disposition", f'attachment; filename="{quote(filename)}"')
            self.end_headers()

            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)

        except Exception as e:
            self.send_error(500, str(e))

    def send_api(self):
        files = self.get_artifact_list()
        data = json.dumps(files, indent=2)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data.encode())))
        self.end_headers()
        self.wfile.write(data.encode())

    def get_artifact_list(self):
        files = []
        if os.path.isdir(self.artifacts_dir):
            for fname in sorted(os.listdir(self.artifacts_dir), key=lambda x: os.path.getmtime(os.path.join(self.artifacts_dir, x)), reverse=True):
                fpath = os.path.join(self.artifacts_dir, fname)
                if os.path.isfile(fpath):
                    info = get_file_info(fpath)
                    info["icon"] = get_icon_for_ext(info["ext"])
                    info["color"] = get_color_for_ext(info["ext"])
                    files.append(info)
        return files

    def render_html(self, files):
        now = datetime.now().strftime("%B %d, %Y at %I:%M %p")

        file_rows = ""
        for f in files:
            file_rows += f"""
            <tr>
                <td style="padding:14px 16px;">
                    <span style="display:inline-block;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:700;background:{f['color']};color:#fff;letter-spacing:1px;">{f['icon']}</span>
                </td>
                <td style="padding:14px 16px;">
                    <span style="color:#e6f1ff;font-weight:600;font-size:14px;">{f['name']}</span>
                    <br/><span style="color:#6a8caf;font-size:12px;">Modified {f['modified']}</span>
                </td>
                <td style="padding:14px 16px;text-align:center;color:#8b949e;font-size:13px;">{f['size']}</td>
                <td style="padding:14px 16px;text-align:center;">
                    <a href="/download/{quote(f['name'])}" style="display:inline-block;padding:7px 18px;background:linear-gradient(135deg,#2563eb,#3b82f6);color:#fff;text-decoration:none;border-radius:6px;font-size:13px;font-weight:600;">Download</a>
                </td>
            </tr>"""

        if not file_rows:
            file_rows = """
            <tr>
                <td colspan="4" style="padding:40px 16px;text-align:center;color:#4a6580;font-size:14px;">
                    No artifacts in the directory yet. Drop files into the artifacts folder to serve them.
                </td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Artifact Server</title>
</head>
<body style="margin:0;padding:0;background-color:#0a0e17;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#0a0e17;">
<tr><td align="center" style="padding:30px 10px;">
<table role="presentation" width="720" cellpadding="0" cellspacing="0" style="max-width:720px;width:100%;">

<tr>
<td style="background:linear-gradient(135deg,#0c1821,#1b2838,#0f2027);padding:32px 36px;border-radius:14px 14px 0 0;border-bottom:3px solid #00d4ff;">
<p style="margin:0 0 4px 0;font-size:11px;color:#00d4ff;letter-spacing:2.5px;text-transform:uppercase;font-weight:600;">Artifact Server</p>
<h1 style="margin:0 0 6px 0;font-size:24px;color:#e6f1ff;">Download Center</h1>
<p style="margin:0;font-size:13px;color:#6a8caf;">Last refreshed: {now} &bull; {len(files)} file(s) available</p>
</td>
</tr>

<tr>
<td style="background:#111b27;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
<thead>
<tr style="border-bottom:1px solid #1e2d3d;">
<td style="padding:10px 16px;font-size:11px;color:#6a8caf;text-transform:uppercase;letter-spacing:1px;width:60px;">Type</td>
<td style="padding:10px 16px;font-size:11px;color:#6a8caf;text-transform:uppercase;letter-spacing:1px;">File</td>
<td style="padding:10px 16px;font-size:11px;color:#6a8caf;text-transform:uppercase;letter-spacing:1px;text-align:center;">Size</td>
<td style="padding:10px 16px;font-size:11px;color:#6a8caf;text-transform:uppercase;letter-spacing:1px;text-align:center;width:120px;">Action</td>
</tr>
</thead>
<tbody>
{file_rows}
</tbody>
</table>
</td>
</tr>

<tr>
<td style="background:#111b27;padding:16px 36px;border-radius:0 0 14px 14px;text-align:center;border-top:1px solid #1e2d3d;">
<p style="margin:0;font-size:11px;color:#334155;letter-spacing:1px;">
Serving files from {self.artifacts_dir}
</p>
</td>
</tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    def log_message(self, format, *args):
        """Suppress request logging for cleaner output."""
        pass


def check_running():
    """Check if server is already running."""
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)
            return pid
        except (ProcessLookupError, PermissionError):
            os.remove(PID_FILE)
    return None


def start_server(host, port, directory):
    """Start the artifact server."""
    # Check if already running
    existing_pid = check_running()
    if existing_pid:
        print(f"Server already running on port {port} (PID {existing_pid})")
        print(f"Access at: http://{host}:{port}/")
        return

    # Validate directory
    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
        print(f"Created artifacts directory: {directory}")

    # Set class variable
    ArtifactHandler.artifacts_dir = directory

    # Change to artifacts directory for static file serving
    os.chdir(directory)

    # Start server in background thread
    with socketserver.TCPServer((host, port), ArtifactHandler) as httpd:
        # Write PID file
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        print(f"Artifact server running on http://{host}:{port}/")
        print(f"Serving files from: {directory}")
        print(f"Press Ctrl+C to stop.")
        print()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)


def stop_server():
    """Stop a running server."""
    pid = check_running()
    if not pid:
        print("No running server found.")
        return
    try:
        os.kill(pid, signal.SIGTERM)
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        print(f"Server stopped (PID {pid}).")
    except ProcessLookupError:
        print("Server process not found.")
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)


def list_server():
    """List running server status."""
    pid = check_running()
    if pid:
        print(f"Server running on PID {pid}")
    else:
        print("No server currently running.")


def main():
    parser = argparse.ArgumentParser(description="Artifact Server — Download center for AI-generated files")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to listen on (default: {DEFAULT_PORT})")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help=f"Host to bind to (default: {DEFAULT_HOST})")
    parser.add_argument("--dir", type=str, default=DEFAULT_DIR, help=f"Directory to serve (default: {DEFAULT_DIR})")
    parser.add_argument("--list", action="store_true", help="List running server")
    parser.add_argument("--stop", action="store_true", help="Stop running server")
    args = parser.parse_args()

    if args.list:
        list_server()
    elif args.stop:
        stop_server()
    else:
        start_server(args.host, args.port, args.dir)


if __name__ == "__main__":
    main()
