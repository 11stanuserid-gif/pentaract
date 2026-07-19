#!/bin/bash
# ============================================
# Pentaract CLI - Termux Cloud Storage Client
# Phone storage bachao, cloud pe save karo!
# ============================================

SERVER="https://pentaract-i2os.onrender.com"
EMAIL="admin@pentaract.io"
PASS="Px9kL2mN7vQ4wR8tY5uI1oP3sA6dF0gH"
STORAGE_ID="516cb035-eb2f-4fce-842e-2c9a7d66458d"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

get_token() {
    curl -s -X POST "$SERVER/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null
}

upload() {
    local file="$1"
    [ ! -f "$file" ] && echo -e "${RED}❌ File not found: $file${NC}" && return 1
    local name=$(basename "$file")
    local size=$(wc -c < "$file")
    echo -e "${BLUE}⬆️  Uploading: $name ($size bytes)${NC}"
    
    local token=$(get_token)
    local code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$SERVER/api/storages/$STORAGE_ID/files/upload" \
        -H "Authorization: Bearer $token" \
        -F "file=@$file" \
        -F "path=")

    [ "$code" = "201" ] && echo -e "${GREEN}✅ Uploaded: $name${NC}" || { echo -e "${RED}❌ Failed (HTTP $code)${NC}"; return 1; }
}

list() {
    local token=$(get_token)
    echo -e "${BLUE}📂 Cloud Files:${NC}"
    curl -s "$SERVER/api/storages/$STORAGE_ID/files/tree/" \
        -H "Authorization: Bearer $token" | python3 -c "
import sys,json
try:
    data = json.load(sys.stdin)
    if not data: print('  (empty)')
    for f in data:
        sz = f.get('size',0)
        if sz < 1024: s = f'{sz} B'
        elif sz < 1048576: s = f'{sz/1024:.1f} KB'
        else: s = f'{sz/1048576:.1f} MB'
        print(f'  📄 {f[\"name\"]}  ({s})')
except: print('  (empty)')
" 2>/dev/null
}

download() {
    local file="$1"
    local dest="${2:-.}"
    [ -z "$file" ] && echo -e "${RED}Usage: pentaract download <filename> [dest]${NC}" && return 1
    
    local token=$(get_token)
    echo -e "${BLUE}⬇️  Downloading: $file${NC}"
    curl -s "$SERVER/api/storages/$STORAGE_ID/files/download/$file" \
        -H "Authorization: Bearer $token" -o "$dest/$file"
    
    [ -f "$dest/$file" ] && echo -e "${GREEN}✅ Saved: $dest/$file${NC}" || echo -e "${RED}❌ Failed${NC}"
}

delete() {
    local file="$1"
    [ -z "$file" ] && echo -e "${RED}Usage: pentaract delete <filename>${NC}" && return 1
    
    local token=$(get_token)
    curl -s -X DELETE "$SERVER/api/storages/$STORAGE_ID/files/$file" \
        -H "Authorization: Bearer $token" > /dev/null
    echo -e "${GREEN}🗑️  Deleted: $file${NC}"
}

backup_folder() {
    local folder="$1"
    [ ! -d "$folder" ] && echo -e "${RED}❌ Folder not found: $folder${NC}" && return 1
    
    local count=0
    find "$folder" -type f | while read -r f; do
        upload "$f"
        count=$((count+1))
    done
    echo -e "${GREEN}✅ Backup complete!${NC}"
}

# Main
case "$1" in
    up|upload)   upload "$2" ;;
    ls|list)     list ;;
    dl|download) download "$2" "$3" ;;
    rm|delete)   delete "$2" ;;
    backup)      backup_folder "$2" ;;
    *)
        echo -e "${BLUE}╔══════════════════════════════════╗${NC}"
        echo -e "${BLUE}║   Pentaract Cloud Storage CLI    ║${NC}"
        echo -e "${BLUE}╚══════════════════════════════════╝${NC}"
        echo ""
        echo "Commands:"
        echo "  pentaract upload <file>      Upload file to cloud"
        echo "  pentaract list               List cloud files"
        echo "  pentaract download <file>    Download from cloud"
        echo "  pentaract delete <file>      Delete from cloud"
        echo "  pentaract backup <folder>    Backup entire folder"
        echo ""
        echo "Examples:"
        echo "  pentaract upload photo.jpg"
        echo "  pentaract list"
        echo "  pentaract download photo.jpg ~/Downloads/"
        echo "  pentaract backup ~/Documents/"
        ;;
esac
