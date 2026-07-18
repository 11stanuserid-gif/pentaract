#!/usr/bin/env python3
"""
Kimi Web UI File Upload Proxy
Sits in front of the kimi web server and injects a file upload button
into the web UI, allowing upload of ANY file type (not just images).
"""

import re
import sys
import json
import io
import os
import uuid
import threading
import http.client
import mimetypes
import time
from urllib.parse import urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler

KIMI_WEB_PORT = 58629
UPLOAD_PORT = 9876
PROXY_PORT = int(os.environ.get("PROXY_PORT", "58629"))
UPLOAD_DIR = os.path.expanduser("~/.kimi-code/mcp-uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

INJECTED_HTML = """
<style>
  /* ===== Kimi-style + button in toolbar ===== */
  .kp-toolbar-btn {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    border: none !important;
    background: transparent !important;
    padding: 4px !important;
    color: inherit !important;
    transition: opacity 0.15s !important;
    line-height: 1 !important;
    outline: none !important;
    border-radius: 4px !important;
  }
  .kp-toolbar-btn:hover { opacity: 0.7 !important; }
  .kp-toolbar-btn svg { width: 16px; height: 16px; display: block; }

  /* ===== Dropdown (positioned above the button) ===== */
  .kp-dropdown {
    position: fixed !important;
    z-index: 999999 !important;
    background: var(--bg-secondary, #1c1c24) !important;
    border: 1px solid var(--border-color, #2c2c36) !important;
    border-radius: 10px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5) !important;
    padding: 4px !important;
    min-width: 170px !important;
    display: none !important;
    backdrop-filter: blur(12px) !important;
    overflow: hidden !important;
  }
  .kp-dropdown.show { display: block !important; }
  .kp-dropdown .kp-item {
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    padding: 9px 14px !important;
    cursor: pointer !important;
    color: var(--text-primary, #e0e0e0) !important;
    font-size: 13px !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    transition: background 0.1s !important;
    border: none !important;
    background: transparent !important;
    width: 100% !important;
    text-align: left !important;
    white-space: nowrap !important;
    border-radius: 6px !important;
  }
  .kp-dropdown .kp-item:hover { background: rgba(255,255,255,0.08) !important; }
  .kp-dropdown .kp-item svg { width: 18px; height: 18px; flex-shrink: 0; opacity: 0.8; }
  .kp-dropdown .kp-item .kp-label { line-height: 1.3; }

  /* ===== Toast & Progress ===== */
  .kp-toast {
    position: fixed !important;
    bottom: 80px !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    z-index: 999999 !important;
    background: var(--bg-secondary, #1c1c24) !important;
    border: 1px solid var(--border-color, #2c2c36) !important;
    border-radius: 10px !important;
    padding: 12px 20px !important;
    color: var(--text-primary, #e0e0e0) !important;
    font-size: 13px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4) !important;
    display: none !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    backdrop-filter: blur(12px) !important;
    pointer-events: none !important;
    text-align: center !important;
  }
  .kp-toast.show { display: block !important; }
  .kp-toast .kp-path { opacity: 0.6; word-break: break-all; font-size: 11px; margin-top: 2px; }

  .kp-progress {
    position: fixed !important;
    bottom: 130px !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    z-index: 999999 !important;
    background: var(--bg-secondary, #1c1c24) !important;
    border: 1px solid var(--border-color, #2c2c36) !important;
    border-radius: 10px !important;
    padding: 12px 20px !important;
    color: var(--text-primary, #e0e0e0) !important;
    font-size: 13px !important;
    min-width: 220px !important;
    display: none !important;
    backdrop-filter: blur(12px) !important;
    text-align: center !important;
  }
  .kp-progress.show { display: block !important; }
  .kp-progress .kp-bar {
    width: 100%; height: 3px; background: rgba(255,255,255,0.08); border-radius: 2px; margin-top: 8px; overflow: hidden;
  }
  .kp-progress .kp-fill {
    height: 100%; background: var(--accent, #6366f1); border-radius: 2px; width: 0%; transition: width 0.3s;
  }
</style>

<input type="file" id="kp-image-input" accept="image/*" multiple style="display:none!important">
<input type="file" id="kp-file-input" multiple style="display:none!important">

<div class="kp-toast" id="kp-toast"><div id="kp-toast-title">Uploaded!</div><div class="kp-path" id="kp-toast-path"></div></div>
<div class="kp-progress" id="kp-progress"><span id="kp-prog-text">Uploading...</span><div class="kp-bar"><div class="kp-fill" id="kp-prog-bar"></div></div></div>

<script>
(function() {
  'use strict';

  var IMG_INP = document.getElementById('kp-image-input');
  var FILE_INP = document.getElementById('kp-file-input');
  var TOAST = document.getElementById('kp-toast');
  var TOAST_T = document.getElementById('kp-toast-title');
  var TOAST_P = document.getElementById('kp-toast-path');
  var PROG = document.getElementById('kp-progress');
  var PROG_T = document.getElementById('kp-prog-text');
  var PROG_B = document.getElementById('kp-prog-bar');

  function toast(title, path) {
    TOAST_T.textContent = title;
    TOAST_P.textContent = path || '';
    TOAST.classList.add('show');
    setTimeout(function(){ TOAST.classList.remove('show'); }, 4000);
  }

  function upload(files) {
    if (!files.length) return;
    var fd = new FormData();
    for (var i = 0; i < files.length; i++) fd.append('files', files[i]);
    PROG.classList.add('show');
    PROG_T.textContent = 'Uploading ' + files.length + ' file(s)...';
    PROG_B.style.width = '0%';
    var x = new XMLHttpRequest();
    x.open('POST', '/__upload__');
    x.upload.onprogress = function(e) {
      if (e.lengthComputable) PROG_B.style.width = (e.loaded / e.total * 80) + '%';
    };
    x.onload = function() {
      PROG_B.style.width = '100%';
      PROG.classList.remove('show');
      try {
        var r = JSON.parse(x.responseText);
        if (r.success) toast('Uploaded ' + r.files.length + ' file(s)', r.files.map(function(f){ return f.split('/').pop(); }).join(', '));
        else toast('Upload failed', r.error || 'Error');
      } catch(_) { toast('Upload failed', 'Parse error'); }
    };
    x.onerror = function() {
      PROG.classList.remove('show');
      toast('Upload failed', 'Network error');
    };
    x.send(fd);
  }

  IMG_INP.addEventListener('change', function(){ upload(this.files); this.value=''; });
  FILE_INP.addEventListener('change', function(){ upload(this.files); this.value=''; });

  /* ---------- toolbar insertion ---------- */
  var DROPDOWN  = null;  // created once, reused
  var activeBtn = null;  // the + button that owns the open dropdown

  function makeDropdown() {
    var dd = document.createElement('div');
    dd.className = 'kp-dropdown';
    dd.innerHTML =
      '<div class="kp-item" data-act="image">' +
        '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="2"/><circle cx="5.5" cy="5.5" r="1.2"/><path d="M14 10l-3-3L2 14"/></svg>' +
        '<span class="kp-label">Upload Image</span>' +
      '</div>' +
      '<div class="kp-item" data-act="file">' +
        '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M10 2H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V6z"/><polyline points="10 2 10 6 14 6"/><line x1="11" y1="9" x2="5" y2="9"/><line x1="11" y1="12" x2="5" y2="12"/></svg>' +
        '<span class="kp-label">Upload File</span>' +
      '</div>';
    dd.addEventListener('click', function(e) {
      var item = e.target.closest('.kp-item');
      if (!item) return;
      dd.classList.remove('show');
      if (item.dataset.act === 'image') IMG_INP.click();
      else FILE_INP.click();
    });
    return dd;
  }

  function posDropdown(btn) {
    if (!DROPDOWN) DROPDOWN = makeDropdown();
    var rect = btn.getBoundingClientRect();
    DROPDOWN.style.left = Math.round(rect.left + rect.width / 2 - 85) + 'px';
    DROPDOWN.style.bottom = (window.innerHeight - rect.top + 8) + 'px';
    return DROPDOWN;
  }

  function addPlusBtn() {
    // Find the native attach button — don't touch it, insert a sibling
    var native = document.querySelector('button.attach-btn');
    if (!native) return false;

    // Already inserted?
    var toolbar = native.parentNode;
    if (toolbar.querySelector('.kp-toolbar-btn')) return true;

    // Create our + button that looks like kimi's native buttons
    var plus = document.createElement('button');
    plus.className = 'kp-toolbar-btn';
    plus.type = 'button';
    plus.title = 'Upload image or file';
    plus.innerHTML = '<svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><line x1="8" y1="2" x2="8" y2="14"/><line x1="2" y1="8" x2="14" y2="8"/></svg>';

    // Insert right after the native attach button
    native.parentNode.insertBefore(plus, native.nextSibling);

    if (!DROPDOWN) {
      DROPDOWN = makeDropdown();
      document.body.appendChild(DROPDOWN);
    }

    plus.addEventListener('click', function(e) {
      e.stopPropagation();
      if (activeBtn && activeBtn !== plus) DROPDOWN.classList.remove('show');
      activeBtn = plus;
      posDropdown(plus);
      DROPDOWN.classList.toggle('show');
    });

    // Close on outside click
    document.addEventListener('click', function() {
      DROPDOWN.classList.remove('show');
    }, false);

    console.log('[KP] + button inserted in toolbar');
    return true;
  }

  // Keep trying — React may recreate the toolbar
  addPlusBtn();
  var mo = new MutationObserver(function(){ addPlusBtn(); });
  mo.observe(document.body, { childList: true, subtree: true });
  setInterval(addPlusBtn, 2000);
})();
</script>
</body>
"""


def inject_upload_button(html):
    """Inject file upload HTML/JS before </body>."""
    if '</body>' in html:
        return html.replace('</body>', INJECTED_HTML)
    return html


class ProxyHandler(BaseHTTPRequestHandler):
    """Reverse proxy that forwards to kimi web server and injects upload feature."""

    def log_message(self, format, *args):
        pass  # Quiet logging

    def do_GET(self):
        if self.path == '/__upload__':
            self.send_error(405, "Method Not Allowed")
            return
        self._proxy_request('GET')

    def do_POST(self):
        if self.path == '/__upload__':
            self._handle_upload()
            return
        self._proxy_request('POST')

    def do_DELETE(self):
        self._proxy_request('DELETE')

    def do_PUT(self):
        self._proxy_request('PUT')

    def do_PATCH(self):
        self._proxy_request('PATCH')

    def do_OPTIONS(self):
        self._proxy_request('OPTIONS')

    def do_HEAD(self):
        self._proxy_request('HEAD')

    def _handle_upload(self):
        """Handle file upload - forward to upload server."""
        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))

        if "multipart/form-data" not in content_type:
            self._send_json({"success": False, "error": "Expected multipart/form-data"}, 400)
            return

        body = self.rfile.read(content_length)

        # Forward to upload server
        try:
            conn = http.client.HTTPConnection("127.0.0.1", UPLOAD_PORT, timeout=30)
            conn.request("POST", "/upload", body, {
                "Content-Type": content_type,
                "Content-Length": str(len(body))
            })
            resp = conn.getresponse()
            data = resp.read()
            conn.close()
            self.send_response(resp.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _proxy_request(self, method):
        """Proxy the request to the kimi web server."""
        parsed = urlparse(self.path)
        path = parsed.path
        if parsed.query:
            path = parsed.path + '?' + parsed.query

        body = None
        content_length = self.headers.get("Content-Length")
        if content_length:
            try:
                body = self.rfile.read(int(content_length))
            except:
                pass

        try:
            conn = http.client.HTTPConnection("127.0.0.1", KIMI_WEB_PORT, timeout=30)
            headers = {}
            for key, val in self.headers.items():
                if key.lower() in ('host', 'connection', 'transfer-encoding', 'content-length', 'accept-encoding'):
                    continue
                headers[key] = val
            headers['Host'] = f'127.0.0.1:{KIMI_WEB_PORT}'

            conn.request(method, path, body=body, headers=headers)

            resp = conn.getresponse()
            resp_body = resp.read()
            status = resp.status

            # Forward response headers
            self.send_response(status)
            for key, val in resp.getheaders():
                if key.lower() in ('transfer-encoding', 'connection', 'content-encoding'):
                    continue
                if key.lower() == 'content-length':
                    continue
                self.send_header(key, val)

            # Inject upload button into HTML responses
            content_type_header = resp.getheader('Content-Type', '')
            if status == 200 and 'text/html' in content_type_header:
                html = resp_body.decode('utf-8', errors='replace')
                modified = inject_upload_button(html)
                modified_bytes = modified.encode('utf-8')
                self.send_header('Content-Length', str(len(modified_bytes)))
                self.end_headers()
                self.wfile.write(modified_bytes)
            else:
                self.send_header('Content-Length', str(len(resp_body)))
                self.end_headers()
                self.wfile.write(resp_body)

            conn.close()
        except Exception as e:
            # If kimi server is unreachable, return error page
            self.send_error(502, f"Kimi Web Server unreachable: {e}")


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def main():
    proxy = ReusableHTTPServer(('0.0.0.0', PROXY_PORT), ProxyHandler)
    print(f"""
{'='*60}
  Kimi Web UI + File Upload Proxy

  Open in browser:  http://localhost:{PROXY_PORT}

  Features added:
  - 📎 File upload button (bottom-right corner)
  - 📁 Any file type supported (not just images)
  - 🔄 Proxies to kimi web (port {KIMI_WEB_PORT})
  - 📦 Uploads stored in: {UPLOAD_DIR}

  Tell the AI: "Maine file upload kar diya hai - filename hai ..."
{'='*60}
""", flush=True)

    try:
        proxy.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        proxy.server_close()


if __name__ == '__main__':
    main()
