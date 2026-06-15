# Artifact Server

Simple HTTP file server for downloading AI-generated artifacts (PDFs, HTML reports, images, etc.) from your browser instead of using WinSCP or file transfer tools.

## What It Does

Serves files from a local directory with a clean, styled web interface that lists all files with type badges, file sizes, modification dates, and one-click download buttons.

## Quick Start

```bash
# Start server (default: port 8082, LAN-accessible)
python3 artifact_server.py

# Open in browser
# http://<server-ip>:8082/
```

Drop files into the served directory and they appear instantly on the page.

## Usage

```bash
# Start server on default port (8082)
python3 artifact_server.py

# Custom port
python3 artifact_server.py --port 9090

# Custom directory
python3 artifact_server.py --dir /path/to/files

# Combined options
python3 artifact_server.py --port 9090 --dir /tmp/downloads

# Stop running server
python3 artifact_server.py --stop

# Check if running
python3 artifact_server.py --list
```

## Endpoints

| Endpoint | Description |
|---|---|
| `/` | Web UI file listing with download buttons |
| `/download/<filename>` | Direct file download (sends as attachment) |
| `/api/files` | JSON API listing all files with metadata |

## Configuration

| Setting | Default | Description |
|---|---|---|
| `--port` | 8082 | Port to listen on |
| `--host` | 0.0.0.0 | Bind address (0.0.0.0 = all interfaces) |
| `--dir` | ~/Documents/ai_workloads/artifacts/ | Directory to serve files from |
| PID file | /tmp/artifact_server.pid | Tracks running server process |

## Requirements

- Python 3.6+ (uses only standard library: `http.server`, `socketserver`, `argparse`, `json`)
- No third-party dependencies

## Firewall (RHEL)

If the server is behind firewalld, open the port:

```bash
sudo firewall-cmd --permanent --add-port=8082/tcp
sudo firewall-cmd --reload
```

## How It Works

1. **Start** — Server binds to the configured port and directory, writes a PID file.
2. **Browse** — Open the web UI in any browser on the LAN. Files are scanned from disk on each page load (no caching).
3. **Download** — Click the download button for any file. Files are served with proper Content-Type headers and `Content-Disposition: attachment` to trigger browser downloads.
4. **Stop** — Run with `--stop` to gracefully shut down, or `Ctrl+C` if running in the foreground.

## Security Notes

- Binds to `0.0.0.0` by default — accessible to any device on the LAN. Use `--host 127.0.0.1` for local-only access.
- Prevents directory traversal in download URLs via `os.path.basename()`.
- No authentication — assume the served directory contains only files you're comfortable sharing on your network.

## File Type Support

The server recognizes 25+ file types with proper MIME types and color-coded badges:

PDF, HTML, TXT, MD, CSV, JSON, PNG, JPG, GIF, SVG, MP4, ZIP, GZ, TAR, PY, SH, YAML, XML, DOCX, XLSX, and more.

## License

MIT
