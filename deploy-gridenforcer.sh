#!/bin/bash
#
# GridEnforcer Deployment Script
# Komplett workflow för Strategi A: Ansible + Backup
#
# Användning:
#   ./deploy-gridenforcer.sh v0.2.0
#

set -e  # Exit vid fel

VERSION=${1:-"v0.1.0"}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
INVENTORY="./ansible_playbooks/inventory.yml"
FETCH_PLAYBOOK="./ansible_playbooks/fetch-ha-config.yml"
BACKUP_SCRIPT="./scripts/ansible_backup_creator.py"
echo "=============================================="
echo "🚀 GridEnforcer Deployment Workflow"
echo "=============================================="
echo "Version: $VERSION"
echo "Timestamp: $TIMESTAMP"
echo ""

# Kontrollera att nödvändiga filer existerar
echo "🔍 Kontrollerar prerequisites..."

if [ ! -f $INVENTORY ]; then
    echo "❌ $INVENTORY hittades inte!"
    echo "💡 Skapa och konfigurera inventory.yml med din HA-server"
    exit 1
fi

if [ ! -f $FETCH_PLAYBOOK ]; then
    echo "❌ $FETCH_PLAYBOOK hittades inte!"
    exit 1
fi

if [ ! -f $BACKUP_SCRIPT ]; then
    echo "❌ $BACKUP_SCRIPT hittades inte!"
    exit 1
fi

if ! command -v ansible-playbook &> /dev/null; then
    echo "❌ ansible-playbook hittades inte!"
    echo "💡 Installera Ansible: pip install ansible"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ python3 hittades inte!"
    exit 1
fi

echo "✅ Prerequisites OK"
echo ""

# Steg 1: Test SSH connection
echo "🔌 Testar SSH-anslutning till Home Assistant..."
if ansible all -i $INVENTORY -m ping; then
    echo "✅ SSH-anslutning fungerar"
else
    echo "❌ SSH-anslutning misslyckades!"
    echo "💡 Kontrollera:"
    echo "   - IP-adress i inventory.yml"
    echo "   - SSH-port (ofta 22222 för SSH addon)"
    echo "   - SSH-nycklar eller lösenord"
    echo "   - Att SSH addon är installerat och startat"
    exit 1
fi
echo ""

# Steg 2: Fetch befintlig HA config
echo "📡 Hämtar befintlig Home Assistant konfiguration..."
echo "   (Detta ändrar INGET på target-systemet)"

# Rensa tidigare fetch om det existerar
if [ -d "fetched_config" ]; then
    echo "🧹 Rensar tidigare fetched config..."
    rm -rf fetched_config
fi

# Kör Ansible playbook för att hämta config
if ansible-playbook $FETCH_PLAYBOOK; then
    echo "✅ HA-konfiguration hämtad framgångsrikt"
else
    echo "❌ Misslyckades att hämta HA-konfiguration!"
    exit 1
fi
echo ""

# Steg 3: Kontrollera vad som hämtades
echo "📋 Kontrollerar hämtad data..."
if [ -d "fetched_config" ]; then
    echo "Hämtade filer:"
    find fetched_config -type f -name "*.yaml" -o -name "*.yml" -o -name "*.json" | head -10
    
    # Räkna hämtade filer
    file_count=$(find fetched_config -type f | wc -l)
    echo "Totalt: $file_count filer hämtade"
else
    echo "❌ Ingen fetched_config directory skapad!"
    exit 1
fi
echo ""

# Steg 4: Hitta hostname från fetched data
echo "🔍 Identifierar target hostname..."
TARGET_HOST=$(ls fetched_config | grep -v system_info.yml | head -1)
if [ -z "$TARGET_HOST" ]; then
    echo "❌ Kunde inte identifiera target hostname!"
    exit 1
fi
echo "Target host: $TARGET_HOST"
echo ""

# Steg 5: Generera merged backup
echo "🔀 Genererar merged backup med GridEnforcer..."
mkdir -p deployment

if python3 $BACKUP_SCRIPT \
    --version "$VERSION" \
    --existing-config-dir "fetched_config/$TARGET_HOST" \
    --output-dir "deployment"; then
    echo "✅ Merged backup genererad framgångsrikt"
else
    echo "❌ Misslyckades att generera backup!"
    exit 1
fi
echo ""

# Steg 6: Hitta och visa skapad backup
echo "📦 Lokaliserar skapad backup..."
BACKUP_FILE=$(find deployment -name "gridenforcer-merged-$VERSION-*.tar" | head -1)

if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup skapad: $(basename "$BACKUP_FILE")"
    echo "📊 Storlek: $BACKUP_SIZE"
    
    # Visa backup innehåll
    echo ""
    echo "📋 Backup innehåll:"
    tar -tf "$BACKUP_FILE"
else
    echo "❌ Kunde inte hitta skapad backup-fil!"
    exit 1
fi
echo ""

# Steg 7: Deployment instruktioner
echo "=============================================="
echo "🎯 DEPLOYMENT INSTRUKTIONER"
echo "=============================================="
echo ""
echo "Backup-fil: $(basename "$BACKUP_FILE")"
echo ""
echo "📝 Nästa steg:"
echo "1. 🔒 Skapa backup av nuvarande HA (säkerhet först!)"
echo "   - Gå till Settings > System > Backups"
echo "   - Klicka 'Create backup' för säkerhet"
echo ""
echo "2. 📤 Överför GridEnforcer backup till Home Assistant:"
echo "   - Öppna Home Assistant i webbläsare"
echo "   - Gå till Settings > System > Backups"
echo "   - Klicka '+' knappen"
echo "   - Välj 'Upload backup'"
echo "   - Välj filen: $(basename "$BACKUP_FILE")"
echo "   - Klicka 'Upload'"
echo ""
echo "3. 🔄 Återställ GridEnforcer backup:"
echo "   - Hitta den uppladdade backupen i listan"
echo "   - Klicka 'Restore' på GridEnforcer backup"
echo "   - Välj 'Home Assistant' (låt addons vara kvar)"
echo "   - Klicka 'Restore'"
echo "   - Vänta på omstart"
echo ""
echo "4. ✅ Verifiera installation:"
echo "   - Logga in i Home Assistant efter omstart"
echo "   - Gå till Settings > Integrations"
echo "   - Leta efter 'GridEnforcer' i listan"
echo "   - Om den inte syns: klicka 'Add Integration' och sök efter GridEnforcer"
echo "   - Kör Developer Tools > Services > python_script.gridenforcer_verify"
echo ""
echo "🛡️  SÄKERHETSNOTERA:"
echo "   Din befintliga konfiguration är PRESERVERAD"
echo "   GridEnforcer läggs till UTAN att ta bort befintliga inställningar"
echo ""
echo "🔧 Support:"
echo "   Om något går fel, återställ din säkerhetsbackup från steg 1"
echo ""

# Steg 8: Spara deployment log
DEPLOY_LOG="deployment/deployment-log-$VERSION-$TIMESTAMP.txt"
{
    echo "GridEnforcer Deployment Log"
    echo "=========================="
    echo "Version: $VERSION"
    echo "Timestamp: $TIMESTAMP"
    echo "Target Host: $TARGET_HOST"
    echo "Backup File: $(basename "$BACKUP_FILE")"
    echo "Backup Size: $BACKUP_SIZE"
    echo ""
    echo "Fetched Config Files:"
    find fetched_config -type f | sort
    echo ""
    echo "Generated Files:"
    ls -la deployment/
} > "$DEPLOY_LOG"

echo "📄 Deployment log sparad: $DEPLOY_LOG"
echo ""
echo "🎉 GridEnforcer deployment förberedd framgångsrikt!"
echo "   Följ instruktionerna ovan för att slutföra installationen."