#!/usr/bin/env python3
"""
Pentaract Real-Time Live Viewer
PostgreSQL-like instant data display — DIRECT PostgreSQL connection
"""

import os
import json
import time
import asyncio
import threading
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.request import Request, urlopen
from datetime import datetime

try:
    import websockets
    import websockets.server
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

# PostgreSQL Config
PG_HOST = "pg-752045-stanuserid-9476.a.aivencloud.com"
PG_PORT = "26183"
PG_USER = "avnadmin"
PG_PASS = "AVNS_RLdM3I4ET4_4ozfXTcN"
PG_DB = "defaultdb"

# Pentaract API (for file download/upload)
Pentaract_API = "https://pentaract-i2os.onrender.com"
ADMIN_EMAIL = "admin@pentaract.io"
ADMIN_PASS = "Px9kL2mN7vQ4wR8tY5uI1oP3sA6dF0gH"

# Global state
current_token = None
token_expiry = 0
connected_clients = set()
last_data_hash = None

def psql_query(query):
    """Execute PostgreSQL query via psql CLI"""
    env = os.environ.copy()
    env['PGPASSWORD'] = PG_PASS
    try:
        result = subprocess.run(
            ['psql', '-h', PG_HOST, '-p', PG_PORT, '-U', PG_USER, '-d', PG_DB,
             '-t', '-A', '-F', '|', '-c', query],
            capture_output=True, text=True, env=env, timeout=10
        )
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"

def psql_query_json(query):
    """Execute query and return as list of dicts"""
    env = os.environ.copy()
    env['PGPASSWORD'] = PG_PASS
    try:
        result = subprocess.run(
            ['psql', '-h', PG_HOST, '-p', PG_PORT, '-U', PG_USER, '-d', PG_DB,
             '-t', '-A', '-F', '|', '-c', query],
            capture_output=True, text=True, env=env, timeout=10
        )
        lines = result.stdout.strip().split('\n')
        rows = []
        for line in lines:
            if line.strip():
                fields = line.split('|')
                rows.append(fields)
        return rows
    except Exception as e:
        return []

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
            token_expiry = time.time() + 1800
            return current_token
    except:
        return ''

def fetch_all_data():
    """Fetch all data from PostgreSQL — real-time"""
    global last_data_hash
    
    tables = {}
    
    # 1. Get storages (no files_amount column — computed from files table)
    storages_raw = psql_query_json(
        "SELECT s.id, s.name, s.chat_id, COUNT(f.id) as file_count FROM storages s LEFT JOIN files f ON f.storage_id = s.id GROUP BY s.id, s.name, s.chat_id;"
    )
    storages = []
    for row in storages_raw:
        if len(row) >= 4:
            storages.append({
                'id': row[0], 'name': row[1],
                'chat_id': row[2], 'files_amount': row[3]
            })
    tables['storages'] = storages
    
    # 2. Get all files
    files_raw = psql_query_json(
        "SELECT id, path, size, storage_id, is_uploaded FROM files ORDER BY path;"
    )
    files = []
    for row in files_raw:
        if len(row) >= 5:
            files.append({
                'id': row[0], 'path': row[1],
                'size': int(row[2]) if row[2].isdigit() else 0,
                'storage_id': row[3],
                'is_uploaded': row[4] == 't'
            })
    tables['files'] = files
    
    # 3. Get users
    users_raw = psql_query_json("SELECT id, email FROM users;")
    users = []
    for row in users_raw:
        if len(row) >= 2:
            users.append({'id': row[0], 'email': row[1]})
    tables['users'] = users
    
    # 4. Get file_chunks count per file (no data column — just count chunks)
    chunks_raw = psql_query_json(
        "SELECT file_id, COUNT(*) as chunk_count FROM file_chunks GROUP BY file_id;"
    )
    chunks = {}
    for row in chunks_raw:
        if len(row) >= 2:
            chunks[row[0]] = {
                'chunk_count': int(row[1]) if row[1].isdigit() else 0,
            }
    tables['chunks'] = chunks
    
    # 5. Get table stats (column is relname not tablename on Aiven)
    stats_raw = psql_query_json(
        "SELECT relname, n_tup_ins, n_tup_upd, n_tup_del FROM pg_stat_user_tables ORDER BY relname;"
    )
    stats = []
    for row in stats_raw:
        if len(row) >= 4:
            stats.append({
                'table': row[0],
                'inserts': row[1], 'updates': row[2], 'deletes': row[3]
            })
    tables['stats'] = stats
    
    # Build hash for change detection
    data_hash = json.dumps(tables, sort_keys=True, default=str)
    changed = data_hash != last_data_hash
    last_data_hash = data_hash
    
    return {'tables': tables, 'changed': changed, 'timestamp': time.time()}

async def notify_clients(data):
    if connected_clients:
        msg = json.dumps(data, default=str)
        await asyncio.gather(*[client.send(msg) for client in connected_clients])

async def poller():
    """Background poller - checks PostgreSQL every 3 seconds"""
    while True:
        try:
            result = fetch_all_data()
            if result.get('changed'):
                await notify_clients({
                    'type': 'data_changed',
                    'tables': result['tables'],
                    'timestamp': result['timestamp']
                })
            else:
                await notify_clients({
                    'type': 'heartbeat',
                    'timestamp': result['timestamp'],
                    'rows': len(result['tables'].get('files', []))
                })
        except Exception as e:
            try:
                await notify_clients({
                    'type': 'error',
                    'message': str(e),
                    'timestamp': time.time()
                })
            except:
                pass
        await asyncio.sleep(3)

async def ws_handler(websocket, path=None):
    connected_clients.add(websocket)
    try:
        # Send initial data
        result = fetch_all_data()
        await websocket.send(json.dumps({
            'type': 'initial_data',
            'tables': result['tables'],
            'timestamp': result['timestamp']
        }))
        
        # Listen for client messages
        async for message in websocket:
            msg = json.loads(message)
            if msg.get('type') == 'refresh':
                result = fetch_all_data()
                await websocket.send(json.dumps({
                    'type': 'data_changed',
                    'tables': result['tables'],
                    'timestamp': result['timestamp']
                }))
            elif msg.get('type') == 'query':
                # Custom SQL query
                sql = msg.get('sql', '')
                if sql.strip().upper().startswith(('SELECT', 'SHOW', 'TABLE', '\\d')):
                    rows = psql_query_json(sql)
                    await websocket.send(json.dumps({
                        'type': 'query_result',
                        'rows': rows,
                        'timestamp': time.time()
                    }))
    finally:
        connected_clients.discard(websocket)

class LiveHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)
    
    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            # Quick health check
            result = psql_query("SELECT COUNT(*) FROM files;")
            self.wfile.write(json.dumps({
                'status': 'ok',
                'pg_connected': 'ERROR' not in result,
                'files_count': result.strip(),
                'timestamp': time.time()
            }).encode())
        elif self.path == '/api/tables':
            self.proxy_pg_query("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
        elif self.path == '/api/files':
            self.proxy_pg_query("SELECT id, path, size, is_uploaded FROM files ORDER BY path;")
        elif self.path == '/api/storages':
            self.proxy_pg_query("SELECT s.id, s.name, s.chat_id, COUNT(f.id) as file_count FROM storages s LEFT JOIN files f ON f.storage_id = s.id GROUP BY s.id, s.name, s.chat_id;")
        elif self.path == '/api/stats':
            self.proxy_pg_query(
                "SELECT relname, n_tup_ins, n_tup_upd, n_tup_del FROM pg_stat_user_tables ORDER BY relname;"
            )
        else:
            super().do_GET()
    
    def proxy_pg_query(self, sql):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        rows = psql_query_json(sql)
        self.wfile.write(json.dumps({'rows': rows, 'count': len(rows)}).encode())
    
    def log_message(self, format, *args):
        pass  # Suppress logs

def run_http(port=8080):
    server = HTTPServer(('0.0.0.0', port), LiveHandler)
    print(f"🌐 HTTP Server: http://0.0.0.0:{port}")
    server.serve_forever()

def run_websocket(port=8081):
    if not WEBSOCKETS_AVAILABLE:
        print("⚠️  WebSocket not available, HTTP polling only")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_forever()
        return
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(poller())
    
    start_server = websockets.serve(ws_handler, '0.0.0.0', port)
    print(f"⚡ WebSocket Server: ws://0.0.0.0:{port}")
    loop.run_until_complete(start_server)
    loop.run_forever()

if __name__ == '__main__':
    print("🚀 Starting Pentaract Live Viewer — PostgreSQL Direct Connection")
    print(f"📊 Database: {PG_HOST}:{PG_PORT}/{PG_DB}")
    print(f"👤 User: {PG_USER}")
    print()
    
    # Test PostgreSQL connection
    result = psql_query("SELECT COUNT(*) FROM files;")
    if 'ERROR' in result:
        print(f"❌ PostgreSQL connection FAILED: {result}")
        print("   Check host, port, password")
    else:
        print(f"✅ PostgreSQL connected — {result.strip()} files found")
    
    # List tables
    tables = psql_query_json("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
    print(f"📋 Tables: {', '.join([t[0] for t in tables if t])}")
    print()
    
    # Start HTTP server in thread
    http_thread = threading.Thread(target=run_http, daemon=True)
    http_thread.start()
    
    # Start WebSocket server
    run_websocket()
