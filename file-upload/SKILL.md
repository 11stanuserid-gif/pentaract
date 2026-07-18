---
name: file-upload
description: >-
  Upload files directly to the AI via a browser-based upload server. Use this when the user
  wants to share files, images, documents, or any data with the AI by uploading them through
  a web interface. The uploaded files are saved to a local directory and can be accessed
  for reading, analysis, or processing. Trigger on phrases like: "upload file", "send file",
  "file bhej", "upload karo", "file share", "file attach", "feeling lazy".
---

# File Upload Skill

Allows the user to upload files to the AI directly through a browser interface.

## How to Use

### Step 1: Start the Upload Server

```bash
cd /opt/render/file-upload
python3 upload-server.py
```

You can customize host/port:
```bash
PORT=9090 python3 upload-server.py
```

### Step 2: Open in Browser

Open `http://localhost:8080` (or your custom port).

### Step 3: Upload Files

- Drag & drop files or click to select
- Click "Upload Files"
- Copy the file path shown, or tell the AI the filename

### Step 4: Tell the AI

Say something like:
- "Maine file upload kar di hai — filename hai report.pdf"
- "I uploaded a file called data.json in uploads"
- "Check karo uploads folder mein"

The AI will read the file from the uploads directory.

## Kimi Web UI Integration (Proxy Mode)

The proxy sits in front of the kimi web UI and replaces the **image attach icon**
with a **+ (plus) icon**. Clicking it shows a dropdown with two options:
**Upload Image** and **Upload File**. This lets you upload **any file type**,
not just images.

### Start the Proxy

```bash
cd /opt/render/file-upload
python3 upload-proxy.py
```

Then open: **http://localhost:58628**

The proxy:
- Forwards all requests to the kimi web server (port 58629)
- Replaces the native attach-image icon with a **+ (plus) button**
- Click + → choose "Upload Image" (image only) or "Upload File" (any type)
- Uploads go to `~/.kimi-code/mcp-uploads/`
- All file types supported, any size

### How to Use

1. Open `http://localhost:58628` in your browser
2. In the chat input area, find the **+ (plus) icon** where the image icon was
3. Click **+** → dropdown shows:
   - **Upload Image** — select images only (preserves original behavior)
   - **Upload File** — select any file type (PDF, ZIP, code, doc, etc.)
4. Upload ho jayega — toast notification aayega
5. Tell the AI: "Maine file upload kar diya hai — filename hai ..."

**Note:** If you were using the original kimi web UI at port 58629, switch to the
proxy URL (port 58628) instead. The UI looks exactly the same except the image
icon is now a **+** icon with both options.

## Features

- **No dependencies** — uses only Python standard library
- **Multiple files** at once
- **Any file type** supported
- **Shows previously uploaded files** with copy-path button
- **Drag & drop** support
- **Proxy mode** — injects upload button into kimi web UI

## File Location

All uploaded files are saved to:
```
/opt/render/file-upload/uploads/
```

Or when using the MCP/upload server:
```
~/.kimi-code/mcp-uploads/
```

The full absolute path is shown after upload and in the file browser.
