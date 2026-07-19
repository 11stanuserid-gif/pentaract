#!/bin/bash
# ============================================
# Pentaract Full Backup — Phone Reset Proof
# Phone ude ya reset ho, data cloud pe safe!
# ============================================

SERVER="https://pentaract-i2os.onrender.com"
EMAIL="admin@pentaract.io"
PASS="Px9kL2mN7vQ4wR8tY5uI1oP3sA6dF0gH"
STORAGE_ID="516cb035-eb2f-4fce-842e-2c9a7d66458d"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

get_token() {
    curl -s -X POST "$SERVER/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null
}

upload_with_path() {
    local file="$1"
    local cloud_path="$2"
    [ ! -f "$file" ] && return 1
    local name=$(basename "$file")
    local token=$(get_token)
    
    # Create folder path in cloud if needed
    if [ -n "$cloud_path" ] && [ "$cloud_path" != "/" ]; then
        create_cloud_folder "$cloud_path" 2>/dev/null
    fi
    
    local code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$SERVER/api/storages/$STORAGE_ID/files/upload" \
        -H "Authorization: Bearer $token" \
        -F "file=@$file" \
        -F "path=$cloud_path")
    
    [ "$code" = "201" ] && return 0 || return 1
}

create_cloud_folder() {
    local folder="$1"
    local token=$(get_token)
    local name=$(basename "$folder")
    local parent=$(dirname "$folder")
    [ "$parent" = "." ] && parent=""
    curl -s -X POST "$SERVER/api/storages/$STORAGE_ID/files/create_folder" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "{\"path\":\"$parent\",\"folder_name\":\"$name\"}" > /dev/null 2>&1
}

# ============================================
# BACKUP: Sab important data cloud pe
# ============================================
backup_all() {
    echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Pentaract Full Backup — Reset Proof ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
    echo ""
    
    local count=0
    local fail=0
    
    # 1. Termux dotfiles & config
    echo -e "${YELLOW}[1/6] Backing up Termux config...${NC}"
    for f in ~/.bashrc ~/.bash_profile ~/.profile ~/.vimrc ~/.gitconfig; do
        [ -f "$f" ] && { upload_with_path "$f" "/" && echo -e "  ${GREEN}✓ $(basename $f)${NC}" && count=$((count+1)) || { echo -e "  ${RED}✗ $(basename $f)${NC}"; fail=$((fail+1)); }; }
    done
    
    # 2. Pentaract scripts
    echo -e "${YELLOW}[2/6] Backing up Pentaract scripts...${NC}"
    for f in ~/pentaract.sh ~/pentaract-live.sh ~/pentaract-backup.sh ~/pentaract-restore.sh; do
        [ -f "$f" ] && { upload_with_path "$f" "/" && echo -e "  ${GREEN}✓ $(basename $f)${NC}" && count=$((count+1)) || { echo -e "  ${RED}✗ $(basename $f)${NC}"; fail=$((fail+1)); }; }
    done
    
    # 3. SSH keys (if any)
    echo -e "${YELLOW}[3/6] Backing up SSH keys...${NC}"
    if [ -d ~/.ssh ]; then
        find ~/.ssh -type f | while read -r f; do
            local name=$(basename "$f")
            # Skip known_hosts and authorized_keys (regenerated)
            [[ "$name" == "known_hosts" || "$name" == "authorized_keys" ]] && continue
            upload_with_path "$f" "/ssh" && echo -e "  ${GREEN}✓ .ssh/$name${NC}" && count=$((count+1)) || { echo -e "  ${RED}✗ .ssh/$name${NC}"; fail=$((fail+1)); }
        done
    fi
    
    # 4. Git repos (just .git/config and important files, not full repo)
    echo -e "${YELLOW}[4/6] Backing up Git configs...${NC}"
    find ~/ -maxdepth 3 -name ".gitconfig" -o -name ".gitignore" 2>/dev/null | head -20 | while read -r f; do
        upload_with_path "$f" "/git" && echo -e "  ${GREEN}✓ $f${NC}" && count=$((count+1))
    done
    
    # 5. Custom scripts & projects
    echo -e "${YELLOW}[5/6] Backing up custom files...${NC}"
    for dir in ~/scripts ~/projects ~/bin; do
        [ -d "$dir" ] && find "$dir" -type f -size -1M 2>/dev/null | while read -r f; do
            local rel="${f#$HOME/}"
            local folder=$(dirname "$rel")
            upload_with_path "$f" "/$folder" && echo -e "  ${GREEN}✓ $rel${NC}" && count=$((count+1))
        done
    done
    
    # 6. Storage link (phone storage)
    echo -e "${YELLOW}[6/6] Backing up storage link...${NC}"
    if [ -f ~/storage/.linked ]; then
        upload_with_path ~/storage/.linked "/storage" && echo -e "  ${GREEN}✓ storage/.linked${NC}" && count=$((count+1))
    fi
    
    # 7. Backup metadata (for restore script)
    echo -e "${YELLOW}[+] Saving backup metadata...${NC}"
    cat > /tmp/backup_manifest.txt << EOF
# Pentaract Backup Manifest
# Date: $(date -Iseconds)
# Device: $(uname -n)
# Termux version: $(termux-info 2>/dev/null | head -1 || echo "unknown")
BACKUP_DATE=$(date -Iseconds)
DEVICE=$(uname -n)
EOF
    upload_with_path /tmp/backup_manifest.txt "/" && echo -e "  ${GREEN}✓ backup_manifest.txt${NC}" && count=$((count+1))
    rm -f /tmp/backup_manifest.txt
    
    echo ""
    echo -e "${GREEN}══════════════════════════════════════${NC}"
    echo -e "${GREEN}Backup complete!${NC}"
    echo -e "  ${GREEN}✓ Uploaded: $count files${NC}"
    [ "$fail" -gt 0 ] && echo -e "  ${RED}✗ Failed: $fail files${NC}"
    echo -e "${GREEN}══════════════════════════════════════${NC}"
    echo ""
    echo -e "${BLUE}Phone reset bhi ho jaye, data safe hai cloud pe!${NC}"
    echo -e "${YELLOW}Restore karne ke liye: bash ~/pentaract-restore.sh${NC}"
}

# ============================================
# LIST: Cloud pe kya hai
# ============================================
list_cloud() {
    echo -e "${BLUE}📂 Cloud Backup Files:${NC}"
    local token=$(get_token)
    curl -s "$SERVER/api/storages/$STORAGE_ID/files/tree/" \
        -H "Authorization: Bearer $token" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data: print('  (empty)')
    for f in data:
        sz = f.get('size',0)
        if sz < 1024: s = f'{sz} B'
        elif sz < 1048576: s = f'{sz/1024:.1f} KB'
        else: s = f'{sz/1048576:.1f} MB'
        print(f'  {f[\"name\"]:40s} {s:>10s}')
except: print('  (empty)')
" 2>/dev/null
}

# Main
case "$1" in
    backup|bak)  backup_all ;;
    list|ls)     list_cloud ;;
    *)
        echo -e "${BLUE}Pentaract Backup — Reset Proof${NC}"
        echo ""
        echo "Commands:"
        echo "  pentaract-backup backup    Full backup to cloud"
        echo "  pentaract-backup list      List cloud files"
        echo ""
        echo "Ye script phone ka pura important data cloud pe save karta hai."
        echo "Phone reset ho ya naya phone ho, pentaract-restore.sh se sab wapas aa jayega."
        ;;
esac
