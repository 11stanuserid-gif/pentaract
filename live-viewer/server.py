#!/usr/bin/env python3
"""
Pentaract Real-Time Live Viewer
PostgreSQL-like instant data display
"""

import os
import json
import time
import asyncio
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.request import Request, urlopen

try:
    import websockets
    import websockets.server
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

# Config
Pentaract_API = "https://pentaract-i2os.onrender.com"
ADMIN_EMAIL = "admin@pentaract.io"
ADMIN_PASS = "Px9kL2mN7vQ4wR8tY5uI1oP3sA6dF0gH"

# Global state
current_token = None
token_expiry = 0
connected_clients = set()
last_files_hash = None

def get_token():
    global current_token, token_expiry
    if current_token and time.time() < token_expiry:
        return current_token
    try:
        data = json.dumps({'email': ADMIN_EMAIL, 'password': ADMIN_PASS}).encode()
        req = Request(f"{Pentaract_API}/api/auth/login", data=data,
                     headers={'Content-Type': 'application/json'}, method='POST')
        with urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            current_token = result.get('access_token', '')
            token_expiry = time.time() + 1800  # 30 min
            return current_token
    except:
        return ''

def fetch_files():
    global last_files_hash
    token = get_token()
    if not token:
        return []
    try:
        # Get storages first
        req = Request(f"{Pentaract_API}/api/storages",
                     headers={'Authorization': f'Bearer {token}'})
        with urlopen(req, timeout=10) as resp:
            storages = json.loads(resp.read())
        
        if not storages.get('storages'):
            return []
        
        storage_id = storages['storages'][0]['id']
        
        # Get files
        req = Request(f"{Pentaract_API}/api/storages/{storage_id}/files",
                     headers={'Authorization': f'Bearer {token}'})
        with urlopen(req, timeout=10) as resp:
            files_data = json.loads(resp.read())
        
        files = files_data.get('files', [])
        files_hash = str(sorted([f.get('name', '') for f in files]))
        
        # Detect changes
        changed = files_hash != last_files_hash
        last_files_hash = files_hash
        
        return {'files': files, 'changed': changed, 'storage_id': storage_id}
    except Exception as e:
        return {'files': [], 'changed': False, 'error': str(e)}

async def notify_clients(data):
    if connected_clients:
        msg = json.dumps(data)
        await asyncio.gather(*[client.send(msg) for client in connected_clients])

async def poller():
    """Background poller - checks for changes every 2 seconds"""
    while True:
        try:
            result = fetch_files()
            if result.get('changed'):
                await notify_clients({
                    'type': 'data_changed',
                    'files': result['files'],
                    'timestamp': time.time()
                })
            else:
                await notify_clients({
                    'type': 'heartbeat',
                    'timestamp': time.time()
                })
        except:
            pass
        await asyncio.sleep(2)

async def ws_handler(websocket, path=None):
    connected_clients.add(websocket)
    try:
        # Send initial data
        result = fetch_files()
        await websocket.send(json.dumps({
            'type': 'initial_data',
            'files': result.get('files', []),
            'timestamp': time.time()
        }))
        
        # Listen for client messages
        async for message in websocket:
            msg = json.loads(message)
            if msg.get('type') == 'refresh':
                result = fetch_files()
                await websocket.send(json.dumps({
                    'type': 'data_changed',
                    'files': result.get('files', []),
                    'timestamp': time.time()
                }))
    finally:
        connected_clients.discard(websocket)

class LiveHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)
    
    def do_GET(self):
        if self.path.startswith('/api/'):
            self.proxy_request('GET')
        else:
            super().do_GET()
    
    def proxy_request(self, method):
        url = f"{Pentaract_API}{self.path}"
        token = get_token()
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
        try:
            req = Request(url, headers=headers, method=method)
            with urlopen(req, timeout=10) as response:
                data = response.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
        except Exception as e:
            self.send_response(500)
            self.end_headers()

def run_http(port=8080):
    server = HTTPServer(('0.0.0.0', port), LiveHandler)
    print(f"🌐 HTTP Server: http://0.0.0.0:{port}")
    server.serve_forever()

def run_websocket(port=8081):
    if not WEBSOCKETS_AVAILABLE:
        print("⚠️  WebSocket not available, using polling only")
        return
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Start poller
    loop.create_task(poller())
    
    # Start websocket server
    start_server = websockets.serve(ws_handler, '0.0.0.0', port)
    print(f"⚡ WebSocket Server: ws://0.0.0.0:{port}")
    loop.run_until_complete(start_server)
    loop.run_forever()

if __name__ == '__main__':
    print("🚀 Starting Pentaract Real-Time Server...")
    print("📊 PostgreSQL-like instant data display")
    print()
    
    # Start HTTP server in thread
    http_thread = threading.Thread(target=run_http, daemon=True)
    http_thread.start()
    
    # Start WebSocket server
    run_websocket()
