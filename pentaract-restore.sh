#!/bin/bash
# ============================================
# Pentaract Restore — Naya phone, purana data!
# Command maro, sab wapas aa jayega!
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

# ============================================
# FULL RESTORE: Sab wapas lao
# ============================================
restore_all() {
    echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Pentaract Restore — Data Wapas Lao!  ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
    echo ""
    
    local token=$(get_token)
    local count=0
    
    # Get file list
    echo -e "${YELLOW}Cloud se files load ho rahi hain...${NC}"
    local files=$(curl -s "$SERVER/api/storages/$STORAGE_ID/files/tree/" \
        -H "Authorization: Bearer $token" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for f in data:
        if f.get('is_file'):
            print(f.get('name', ''))
except: pass
" 2>/dev/null)
    
    if [ -z "$files" ]; then
        echo -e "${RED}Cloud pe koi files nahi hain!${NC}"
        return 1
    fi
    
    echo "$files" | while read -r filename; do
        [ -z "$filename" ] && continue
        
        echo -e "${BLUE}  Downloading: $filename${NC}"
        
        # Determine where to restore based on filename
        local dest=""
        case "$filename" in
            *.sh)           dest="$HOME" ;;
            .bashrc|.bash_profile|.profile|.vimrc|.gitconfig)  dest="$HOME" ;;
            backup_manifest.txt)  dest="/tmp" ;;
            *)              dest="$HOME" ;;
        esac
        
        curl -s "$SERVER/api/storages/$STORAGE_ID/files/download/$filename" \
            -H "Authorization: Bearer $token" \
            -o "$dest/$filename" 2>/dev/null
        
        if [ -f "$dest/$filename" ]; then
            echo -e "  ${GREEN}✓ Restored: $dest/$filename${NC}"
            chmod +x "$dest/$filename" 2>/dev/null
            count=$((count+1))
        else
            echo -e "  ${RED}✗ Failed: $filename${NC}"
        fi
    done
    
    # Make scripts executable
    chmod +x ~/pentaract.sh ~/pentaract-live.sh ~/pentaract-backup.sh ~/pentaract-restore.sh 2>/dev/null
    
    echo ""
    echo -e "${GREEN}══════════════════════════════════════${NC}"
    echo -e "${GREEN}Restore complete! $count files wapas aa gaye!${NC}"
    echo -e "${GREEN}══════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. source ~/.bashrc"
    echo "  2. bash ~/pentaract.sh list    # Check cloud files"
    echo "  3. bash ~/pentaract.sh upload  # Upload new files"
}

# ============================================
# QUICK SETUP: Naya phone pe pehli baar
# ============================================
quick_setup() {
    echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Pentaract Quick Setup — New Phone!   ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
    echo ""
    
    echo -e "${YELLOW}Step 1: Termux packages install ho rahe hain...${NC}"
    pkg update -y > /dev/null 2>&1
    pkg install -y python curl git > /dev/null 2>&1
    echo -e "${GREEN}  ✓ Packages installed${NC}"
    
    echo -e "${YELLOW}Step 2: Storage permission...${NC}"
    termux-setup-storage > /dev/null 2>&1
    echo -e "${GREEN}  ✓ Storage linked${NC}"
    
    echo -e "${YELLOW}Step 3: Pentaract scripts download ho rahe hain...${NC}"
    curl -sL "https://raw.githubusercontent.com/11stanuserid-gif/pentaract/main/pentaract.sh" -o ~/pentaract.sh
    curl -sL "https://raw.githubusercontent.com/11stanuserid-gif/pentaract/main/pentaract-live.sh" -o ~/pentaract-live.sh
    curl -sL "https://raw.githubusercontent.com/11stanuserid-gif/pentaract/main/pentaract-backup.sh" -o ~/pentaract-backup.sh
    
    # Save this restore script itself
    cat > ~/pentaract-restore.sh << 'RESTORE_SCRIPT'
#!/bin/bash
# Quick restore — just run: bash ~/pentaract-restore.sh restore
curl -sL "https://raw.githubusercontent.com/11stanuserid-gif/pentaract/main/pentaract-restore.sh" -o /tmp/pr-restore.sh
bash /tmp/pr-restore.sh restore
RESTORE_SCRIPT
    chmod +x ~/pentaract*.sh
    echo -e "${GREEN}  ✓ Scripts downloaded${NC}"
    
    echo -e "${YELLOW}Step 4: Cloud se data restore ho raha hai...${NC}"
    restore_all
    
    echo ""
    echo -e "${GREEN}══════════════════════════════════════${NC}"
    echo -e "${GREEN}Setup complete! Sab data wapas hai!${NC}"
    echo -e "${GREEN}══════════════════════════════════════${NC}"
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
    restore)   restore_all ;;
    setup)     quick_setup ;;
    list|ls)   list_cloud ;;
    *)
        echo -e "${BLUE}Pentaract Restore — Data Wapas Lao!${NC}"
        echo ""
        echo "Commands:"
        echo "  pentaract-restore restore    Cloud se sab data restore karo"
        echo "  pentaract-restore setup      Naya phone pe full setup + restore"
        echo "  pentaract-restore list       Cloud pe kya hai dekho"
        echo ""
        echo -e "${YELLOW}Naya phone hai? Ye karo:${NC}"
        echo "  1. Termux install karo"
        echo "  2. bash ~/pentaract-restore.sh setup"
        echo "  3. Bas! Sab data wapas aa jayega!"
        ;;
esac
