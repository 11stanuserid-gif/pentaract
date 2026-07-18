#!/usr/bin/env python3
"""
File Upload Server - Direct file upload via browser.
Run this server, then open http://localhost:8080 to upload files.
"""

import os
import sys
import json
import html
import uuid
import base64
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from io import BytesIO

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))

os.makedirs(UPLOAD_DIR, exist_ok=True)

UPLOAD_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>File Upload</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #0f0f13; color: #e0e0e0; min-height: 100vh;
      display: flex; align-items: center; justify-content: center;
    }
    .container { max-width: 600px; width: 100%; padding: 2rem; }
    h1 { font-size: 1.5rem; margin-bottom: 0.5rem; color: #fff; }
    p.sub { color: #888; margin-bottom: 2rem; font-size: 0.9rem; }
    .upload-zone {
      border: 2px dashed #333; border-radius: 12px; padding: 3rem 2rem;
      text-align: center; cursor: pointer; transition: all 0.3s;
      background: #1a1a22;
    }
    .upload-zone:hover, .upload-zone.dragover {
      border-color: #6366f1; background: #1e1e2a;
    }
    .upload-zone.has-file { border-color: #22c55e; background: #1a2a1e; }
    .upload-zone .icon { font-size: 3rem; margin-bottom: 1rem; }
    .upload-zone p { color: #aaa; }
    .upload-zone .hint { font-size: 0.8rem; color: #555; margin-top: 0.5rem; }
    #file-input { display: none; }
    #file-list { margin-top: 1rem; }
    .file-item {
      display: flex; align-items: center; justify-content: space-between;
      padding: 0.5rem 0.75rem; background: #1a1a22; border-radius: 8px;
      margin-bottom: 0.5rem; font-size: 0.9rem;
    }
    .file-item .name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .file-item .size { color: #888; margin-left: 0.5rem; font-size: 0.8rem; }
    .file-item .remove { color: #ef4444; cursor: pointer; margin-left: 0.5rem; font-weight: bold; }
    #upload-btn {
      display: block; width: 100%; margin-top: 1.5rem; padding: 0.85rem;
      background: #6366f1; color: #fff; border: none; border-radius: 8px;
      font-size: 1rem; font-weight: 600; cursor: pointer; transition: background 0.3s;
    }
    #upload-btn:hover { background: #5558e6; }
    #upload-btn:disabled { background: #333; color: #666; cursor: not-allowed; }
    #status { margin-top: 1.5rem; padding: 1rem; border-radius: 8px; display: none; }
    #status.success { display: block; background: #1a2e1a; border: 1px solid #22c55e; color: #86efac; }
    #status.error { display: block; background: #2e1a1a; border: 1px solid #ef4444; color: #fca5a5; }
    #status.loading { display: block; background: #1a1a2e; border: 1px solid #6366f1; color: #a5b4fc; }
    .files-list { margin-top: 2rem; }
    .files-list h3 { font-size: 0.9rem; color: #888; margin-bottom: 0.5rem; }
    .files-list ul { list-style: none; }
    .files-list li {
      padding: 0.3rem 0; font-size: 0.85rem; color: #aaa;
      display: flex; justify-content: space-between;
    }
    .files-list li a { color: #6366f1; text-decoration: none; }
    .files-list li a:hover { text-decoration: underline; }
    .copy-path {
      background: none; border: 1px solid #333; color: #888; padding: 0.1rem 0.4rem;
      border-radius: 4px; cursor: pointer; font-size: 0.75rem; margin-left: 0.5rem;
    }
    .copy-path:hover { border-color: #6366f1; color: #6366f1; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Upload Files</h1>
    <p class="sub">Drop files below to share them with the AI</p>

    <div class="upload-zone" id="drop-zone">
      <div class="icon">&#128206;</div>
      <p><strong>Click to select</strong> or drag & drop files here</p>
      <p class="hint">Any file type, no size limit</p>
    </div>
    <input type="file" id="file-input" multiple>

    <div id="file-list"></div>
    <button id="upload-btn" disabled>Upload Files</button>
    <div id="status"></div>

    <div class="files-list" id="uploaded-files">
      <h3>Previously Uploaded Files</h3>
      <ul id="file-browser">
        <li style="color:#555; font-size:0.8rem;">Loading...</li>
      </ul>
    </div>
  </div>

  <script>
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileList = document.getElementById('file-list');
    const uploadBtn = document.getElementById('upload-btn');
    const status = document.getElementById('status');
    const fileBrowser = document.getElementById('file-browser');
    let selectedFiles = [];

    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => { e.preventDefault(); dropZone.classList.remove('dragover'); handleFiles(e.dataTransfer.files); });
    fileInput.addEventListener('change', () => handleFiles(fileInput.files));

    function handleFiles(files) {
      for (let f of files) {
        if (!selectedFiles.find(s => s.name === f.name && s.size === f.size)) {
          selectedFiles.push(f);
        }
      }
      renderFileList();
    }

    function renderFileList() {
      fileList.innerHTML = '';
      if (selectedFiles.length === 0) { uploadBtn.disabled = true; dropZone.classList.remove('has-file'); return; }
      uploadBtn.disabled = false; dropZone.classList.add('has-file');
      selectedFiles.forEach((f, i) => {
        const div = document.createElement('div'); div.className = 'file-item';
        div.innerHTML = '<span class="name">' + htmlEscape(f.name) + '</span>' +
          '<span class="size">' + formatSize(f.size) + '</span>' +
          '<span class="remove" data-index="' + i + '">&times;</span>';
        div.querySelector('.remove').addEventListener('click', () => {
          selectedFiles.splice(i, 1); renderFileList();
        });
        fileList.appendChild(div);
      });
    }

    uploadBtn.addEventListener('click', () => {
      if (selectedFiles.length === 0) return;
      status.className = 'loading'; status.textContent = 'Uploading...'; status.style.display = 'block';
      uploadBtn.disabled = true;

      const formData = new FormData();
      for (let f of selectedFiles) formData.append('files', f);

      fetch('/upload', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(d => {
          if (d.success) {
            status.className = 'success';
            status.innerHTML = d.files.map(f => '<code>' + htmlEscape(f) + '</code>').join('<br>') + '<br><strong>Uploaded!</strong>';
            selectedFiles = []; renderFileList();
            loadFileList();
          } else {
            status.className = 'error'; status.textContent = 'Error: ' + (d.error || 'Unknown');
          }
        })
        .catch(e => { status.className = 'error'; status.textContent = 'Error: ' + e.message; })
        .finally(() => { uploadBtn.disabled = false; });
    });

    function loadFileList() {
      fetch('/files').then(r => r.json()).then(d => {
        if (d.files.length === 0) { fileBrowser.innerHTML = '<li style="color:#555;font-size:0.8rem;">No files uploaded yet</li>'; return; }
        fileBrowser.innerHTML = '';
        d.files.forEach(f => {
          const li = document.createElement('li');
          li.innerHTML = '<span><a href="/download/' + encodeURIComponent(f.name) + '" target="_blank">' + htmlEscape(f.name) + '</a> <span style="color:#666;font-size:0.8rem;">' + formatSize(f.size) + '</span></span>' +
            '<span><code style="color:#555;font-size:0.75rem;">' + htmlEscape(f.path) + '</code> <button class="copy-path" data-path="' + htmlEscape(f.path) + '">Copy</button></span>';
          li.querySelector('.copy-path').addEventListener('click', function() {
            navigator.clipboard.writeText(this.dataset.path).then(() => {
              this.textContent = 'Copied!'; setTimeout(() => { this.textContent = 'Copy'; }, 2000);
            });
          });
          fileBrowser.appendChild(li);
        });
      }).catch(() => { fileBrowser.innerHTML = '<li style="color:#ef4444;font-size:0.8rem;">Could not load file list</li>'; });
    }

    function htmlEscape(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
    function formatSize(bytes) {
      if (bytes < 1024) return bytes + ' B';
      if (bytes < 1024*1024) return (bytes/1024).toFixed(1) + ' KB';
      return (bytes/(1024*1024)).toFixed(1) + ' MB';
    }
    loadFileList();
  </script>
</body>
</html>"""


class UploadHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler with file upload support."""

    def log_message(self, format, *args):
        """Log to stdout with timestamp."""
        import datetime
        sys.stderr.write("[%s] %s - %s\n" % (
            datetime.datetime.now().strftime("%H:%M:%S"),
            self.client_address[0],
            format % args
        ))

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_html(self, html_content, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html_content.encode())

    def _send_file(self, filepath):
        if not os.path.isfile(filepath):
            self._send_json({"error": "File not found"}, 404)
            return
        mime_type, _ = mimetypes.guess_type(filepath)
        if mime_type is None:
            mime_type = "application/octet-stream"
        file_size = os.path.getsize(filepath)
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Content-Disposition",
                         f'attachment; filename="{os.path.basename(filepath)}"')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        with open(filepath, "rb") as f:
            self.wfile.write(f.read())

    def _list_uploaded_files(self):
        files = []
        if os.path.isdir(UPLOAD_DIR):
            for fname in sorted(os.listdir(UPLOAD_DIR), key=lambda x: os.path.getmtime(os.path.join(UPLOAD_DIR, x)), reverse=True):
                fpath = os.path.join(UPLOAD_DIR, fname)
                if os.path.isfile(fpath):
                    files.append({
                        "name": fname,
                        "size": os.path.getsize(fpath),
                        "path": os.path.abspath(fpath),
                        "mtime": os.path.getmtime(fpath)
                    })
        return files

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._send_html(UPLOAD_PAGE)

        elif path == "/files":
            self._send_json({"files": self._list_uploaded_files()})

        elif path.startswith("/download/"):
            filename = path[len("/download/"):]
            safe_path = os.path.normpath(os.path.join(UPLOAD_DIR, filename))
            if not safe_path.startswith(os.path.normpath(UPLOAD_DIR)):
                self._send_json({"error": "Invalid path"}, 400)
                return
            self._send_file(safe_path)

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/upload":
            content_type = self.headers.get("Content-Type", "")
            content_length = int(self.headers.get("Content-Length", 0))

            if "multipart/form-data" not in content_type:
                self._send_json({"error": "Expected multipart/form-data"}, 400)
                return

            boundary = content_type.split("boundary=")[1].strip()
            if boundary.startswith('"') and boundary.endswith('"'):
                boundary = boundary[1:-1]

            body = self.rfile.read(content_length)
            uploaded_files = self._parse_multipart(body, boundary)

            if not uploaded_files:
                self._send_json({"error": "No files received"}, 400)
                return

            saved_paths = []
            for filename, data in uploaded_files:
                # Sanitize filename
                safe_name = os.path.basename(filename)
                # Add timestamp prefix to avoid overwrites
                ts = str(uuid.uuid4())[:8]
                name, ext = os.path.splitext(safe_name)
                safe_name = f"{name}_{ts}{ext}"
                save_path = os.path.join(UPLOAD_DIR, safe_name)
                with open(save_path, "wb") as f:
                    f.write(data)
                saved_paths.append(os.path.abspath(save_path))
                print(f"[UPLOAD] Saved: {save_path} ({len(data)} bytes)")

            self._send_json({"success": True, "files": saved_paths})
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _parse_multipart(self, body, boundary):
        """Parse multipart form data and return list of (filename, data) tuples."""
        results = []
        boundary_bytes = boundary.encode()
        delimiter = b"--" + boundary_bytes
        delimiter_end = b"--" + boundary_bytes + b"--"

        parts = body.split(delimiter)
        for part in parts:
            if part == b"" or part.startswith(b"--"):
                continue
            # Split headers from body
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue
            headers_raw = part[:header_end].decode("utf-8", errors="replace")
            data = part[header_end + 4:]
            # Remove trailing \r\n
            if data.endswith(b"\r\n"):
                data = data[:-2]

            # Check for filename in Content-Disposition
            filename = None
            for line in headers_raw.split("\r\n"):
                if line.lower().startswith("content-disposition"):
                    for segment in line.split(";"):
                        segment = segment.strip()
                        if segment.startswith('filename="'):
                            filename = segment[9:-1]
                        elif segment.startswith("filename="):
                            filename = segment[9:]
            if filename and data:
                results.append((filename, data))
        return results


def main():
    server = HTTPServer((HOST, PORT), UploadHandler)
    print(f"""
{'='*60}
  File Upload Server is running!

  Open in browser:  http://localhost:{PORT}
  Upload directory: {os.path.abspath(UPLOAD_DIR)}

  Tell the AI: "I uploaded files in /uploads/"
{'='*60}
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
