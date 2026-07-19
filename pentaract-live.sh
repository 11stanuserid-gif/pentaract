#!/bin/bash
# ============================================
# Pentaract Live Sync - Zero Phone Storage
# Sab cloud pe, phone pe kuch nahi!
# ============================================

SERVER="https://pentaract-i2os.onrender.com"
EMAIL="admin@pentaract.io"
PASS="Px9kL2mN7vQ4wR8tY5uI1oP3sA6dF0gH"
STORAGE_ID="516cb035-eb2f-4fce-842e-2c9a7d66458d"
WORKSPACE="/tmp/pentaract_workspace"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "$WORKSPACE"

# Get auth token
get_token() {
    curl -s -X POST "$SERVER/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null
}

# Start session - download all files from cloud
start_session() {
    echo -e "${BLUE}Starting live session...${NC}"
    TOKEN=$(get_token)
    
    # List all cloud files using tree endpoint
    curl -s "$SERVER/api/storages/$STORAGE_ID/files/tree/" \
        -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data:
        for f in data:
            print(f.get('name', ''))
except: pass
" 2>/dev/null | while read -r filename; do
        if [ -n "$filename" ]; then
            echo -e "${GREEN}Loading: $filename${NC}"
            # Download file content
            curl -s "$SERVER/api/storages/$STORAGE_ID/files/download/$filename" \
                -H "Authorization: Bearer $TOKEN" \
                -o "$WORKSPACE/$filename" 2>/dev/null
        fi
    done
    
    echo -e "${GREEN}Session started! Files in: $WORKSPACE${NC}"
    echo -e "${YELLOW}Work in: $WORKSPACE${NC}"
    cd "$WORKSPACE"
}

# Upload file to cloud using multipart
upload_file() {
    local file="$1"
    [ ! -f "$file" ] && echo -e "${RED}File not found: $file${NC}" && return 1
    
    TOKEN=$(get_token)
    local name=$(basename "$file")
    echo -e "${GREEN}Uploading: $name${NC}"
    
    local code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$SERVER/api/storages/$STORAGE_ID/files/upload" \
        -H "Authorization: Bearer $TOKEN" \
        -F "file=@$file" \
        -F "path=")

    [ "$code" = "201" ] && echo -e "${GREEN}Uploaded: $name${NC}" || { echo -e "${RED}Failed (HTTP $code)${NC}"; return 1; }
}

# Sync - upload all local files to cloud
sync() {
    echo -e "${BLUE}Syncing to cloud...${NC}"
    
    find "$WORKSPACE" -type f | while read -r file; do
        upload_file "$file"
    done
    
    echo -e "${GREEN}All files synced to cloud!${NC}"
}

# Save specific file to cloud
save() {
    local file="$1"
    [ -z "$file" ] && echo -e "${RED}Usage: save <filename>${NC}" && return 1
    [ ! -f "$WORKSPACE/$file" ] && echo -e "${RED}File not found in workspace: $file${NC}" && return 1
    
    upload_file "$WORKSPACE/$file"
}

# Load specific file from cloud
load() {
    local file="$1"
    [ -z "$file" ] && echo -e "${RED}Usage: load <filename>${NC}" && return 1
    
    TOKEN=$(get_token)
    echo -e "${GREEN}Loading: $file${NC}"
    
    curl -s "$SERVER/api/storages/$STORAGE_ID/files/download/$file" \
        -H "Authorization: Bearer $TOKEN" \
        -o "$WORKSPACE/$file" 2>/dev/null
    
    [ -f "$WORKSPACE/$file" ] && echo -e "${GREEN}Loaded! Edit: nano $WORKSPACE/$file${NC}" || echo -e "${RED}Failed${NC}"
}

# Create new file directly in cloud
create() {
    local file="$1"
    local content="$2"
    [ -z "$file" ] && echo -e "${RED}Usage: create <filename> <content>${NC}" && return 1
    
    # Create temp file with content
    echo "$content" > "$WORKSPACE/$file"
    upload_file "$WORKSPACE/$file"
    rm -f "$WORKSPACE/$file"
}

# End session - sync and cleanup
end_session() {
    echo -e "${YELLOW}Ending session...${NC}"
    sync
    rm -rf "$WORKSPACE"
    echo -e "${GREEN}Session ended! Phone storage freed!${NC}"
}

# List cloud files
list() {
    echo -e "${BLUE}Cloud Files:${NC}"
    TOKEN=$(get_token)
    curl -s "$SERVER/api/storages/$STORAGE_ID/files/tree/" \
        -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data: print('  (empty)')
    for f in data:
        sz = f.get('size',0)
        if sz < 1024: s = f'{sz} B'
        elif sz < 1048576: s = f'{sz/1024:.1f} KB'
        else: s = f'{sz/1048576:.1f} MB'
        print(f'  {f[\"name\"]}  ({s})')
except: print('  (empty)')
" 2>/dev/null
}

# Show current workspace status
status() {
    echo -e "${BLUE}Workspace Status:${NC}"
    if [ -d "$WORKSPACE" ]; then
        echo -e "${GREEN}Workspace: $WORKSPACE${NC}"
        echo -e "${YELLOW}Files locally:${NC}"
        ls -la "$WORKSPACE" 2>/dev/null
    else
        echo -e "${YELLOW}No active session. Run: start${NC}"
    fi
}

# Main menu
case "$1" in
    start)    start_session ;;
    sync)     sync ;;
    save)     save "$2" ;;
    load)     load "$2" ;;
    end)      end_session ;;
    create)   create "$2" "$3" ;;
    list)     list ;;
    status)   status ;;
    *)
        echo -e "${BLUE}Pentaract Live Sync - Zero Storage${NC}"
        echo ""
        echo -e "${GREEN}Commands:${NC}"
        echo "  start          - Start session (load all files from cloud)"
        echo "  sync           - Upload all changes to cloud"
        echo "  save <file>    - Save specific file to cloud"
        echo "  load <file>    - Load specific file from cloud"
        echo "  create <file> <content> - Create file directly in cloud"
        echo "  list           - List all cloud files"
        echo "  status         - Show workspace status"
        echo "  end            - End session (sync + cleanup)"
        echo ""
        echo -e "${YELLOW}Usage:${NC}"
        echo "  1. bash ~/pentaract-live.sh start"
        echo "  2. nano /tmp/pentaract_workspace/file.txt"
        echo "  3. bash ~/pentaract-live.sh save file.txt"
        echo "  4. bash ~/pentaract-live.sh end"
        ;;
esac
