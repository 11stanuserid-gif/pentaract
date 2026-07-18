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
    echo -e "${BLUE}🔄 Starting live session...${NC}"
    TOKEN=$(get_token)
    
    # List all cloud files
    FILES=$(curl -s "$SERVER/api/storages/$STORAGE_ID/files" \
        -H "Authorization: Bearer $TOKEN")
    
    echo "$FILES" | python3 -c "
import sys, json
data = json.load(sys.stdin)
files = data if isinstance(data, list) else data.get('files', [])
for f in files:
    print(f.get('path', f.get('name', '')))
" 2>/dev/null | while read -r filepath; do
        if [ -n "$filepath" ]; then
            echo -e "${GREEN}📥 Loading: $filepath${NC}"
            # Download file content
            CONTENT=$(curl -s "$SERVER/api/storages/$STORAGE_ID/files/$filepath" \
                -H "Authorization: Bearer $TOKEN" \
                -o - 2>/dev/null)
            echo "$CONTENT" > "$WORKSPACE/$filepath" 2>/dev/null
        fi
    done
    
    echo -e "${GREEN}✅ Session started! Files in: $WORKSPACE${NC}"
    echo -e "${YELLOW}📝 Work in: $WORKSPACE${NC}"
    cd "$WORKSPACE"
}

# Sync - upload all changed files back to cloud
sync() {
    echo -e "${BLUE}🔄 Syncing to cloud...${NC}"
    TOKEN=$(get_token)
    
    find "$WORKSPACE" -type f | while read -r file; do
        REL_PATH="${file#$WORKSPACE/}"
        echo -e "${GREEN}📤 Uploading: $REL_PATH${NC}"
        
        curl -s -X POST "$SERVER/api/storages/$STORAGE_ID/files" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"path\":\"$REL_PATH\",\"content\":\"$(cat "$file" | base64 -w0)\"}" \
            > /dev/null 2>&1
    done
    
    echo -e "${GREEN}✅ All files synced to cloud!${NC}"
}

# Save specific file
save() {
    local file="$1"
    [ -z "$file" ] && echo -e "${RED}Usage: save <filename>${NC}" && return 1
    [ ! -f "$WORKSPACE/$file" ] && echo -e "${RED}File not found: $file${NC}" && return 1
    
    TOKEN=$(get_token)
    echo -e "${GREEN}📤 Saving: $file${NC}"
    
    curl -s -X POST "$SERVER/api/storages/$STORAGE_ID/files" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"path\":\"$file\",\"content\":\"$(cat "$WORKSPACE/$file" | base64 -w0)\"}"
    
    echo -e "${GREEN}✅ Saved to cloud!${NC}"
}

# Load specific file
load() {
    local file="$1"
    [ -z "$file" ] && echo -e "${RED}Usage: load <filename>${NC}" && return 1
    
    TOKEN=$(get_token)
    echo -e "${GREEN}📥 Loading: $file${NC}"
    
    CONTENT=$(curl -s "$SERVER/api/storages/$STORAGE_ID/files/$file" \
        -H "Authorization: Bearer $TOKEN" \
        -o - 2>/dev/null)
    
    echo "$CONTENT" > "$WORKSPACE/$file"
    echo -e "${GREEN}✅ Loaded! Edit: nano $WORKSPACE/$file${NC}"
}

# End session - sync and cleanup
end_session() {
    echo -e "${YELLOW}🔄 Ending session...${NC}"
    sync
    rm -rf "$WORKSPACE"
    echo -e "${GREEN}✅ Session ended! Phone storage freed!${NC}"
}

# Create new file directly in cloud
create() {
    local file="$1"
    local content="$2"
    [ -z "$file" ] && echo -e "${RED}Usage: create <filename> <content>${NC}" && return 1
    
    TOKEN=$(get_token)
    echo -e "${GREEN}📝 Creating: $file${NC}"
    
    curl -s -X POST "$SERVER/api/storages/$STORAGE_ID/files" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"path\":\"$file\",\"content\":\"$content\"}"
    
    echo -e "${GREEN}✅ Created in cloud!${NC}"
}

# List cloud files
list() {
    echo -e "${BLUE}📂 Cloud Files:${NC}"
    TOKEN=$(get_token)
    curl -s "$SERVER/api/storages/$STORAGE_ID/files" \
        -H "Authorization: Bearer $TOKEN" \
        | python3 -c "
import sys, json
data = json.load(sys.stdin)
files = data if isinstance(data, list) else data.get('files', [])
for f in files:
    name = f.get('path', f.get('name', 'unknown'))
    size = f.get('size', '?')
    print(f'  📄 {name}  ({size} B)')
" 2>/dev/null
}

# Show current workspace status
status() {
    echo -e "${BLUE}📊 Workspace Status:${NC}"
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
        echo -e "${BLUE}╔═══════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║   Pentaract Live Sync - Zero Storage  ║${NC}"
        echo -e "${BLUE}╚═══════════════════════════════════════╝${NC}"
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
        echo "  1. pentaract-live start    # Session start"
        echo "  2. nano /tmp/pentaract_workspace/file.txt  # Edit"
        echo "  3. pentaract-live save file.txt  # Save to cloud"
        echo "  4. pentaract-live end      # Cleanup phone storage"
        ;;
esac
