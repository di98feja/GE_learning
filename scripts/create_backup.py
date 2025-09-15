#!/usr/bin/env python3
"""
GridEnforcer Backup Creator
Skapar Home Assistant-kompatibla backup-filer för GridEnforcer deployment
"""

import json
import tarfile
import tempfile
import argparse
import sys
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import yaml


class GridEnforcerBackupCreator:
    """Skapar HA-kompatibla backup-filer för GridEnforcer deployment"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.integration_path = self.project_root / "custom_components" / "gridenforcer"
        self.packages_path = self.project_root / "packages" / "gridenforcer"
        self.templates_path = self.project_root / "deployment-templates"
        
    def create_ha_backup_metadata(self, version: str, deployment_type: str) -> Dict:
        """Skapa HA-kompatibel backup metadata (exakt som HA gör)"""
        
        timestamp = datetime.now(timezone.utc).isoformat()
        instance_id = str(uuid.uuid4())
        
        # Exakt samma format som HA använder
        return {
            "slug": f"gridenforcer-{version.replace('v', '').replace('.', '-')}",
            "version": 2,  # HA backup format version (måste vara integer)
            "name": f"GridEnforcer {version} ({deployment_type})",
            "date": timestamp,
            "type": "partial",
            "supervisor_version": "2025.09.0",
            "extra": {
                "instance_id": instance_id,
                "gridenforcer_deployment": True,
                "created_by": "gridenforcer_ci_cd"
            },
            "addons": [],  # Inga addons i denna backup
            "homeassistant": {
                "version": "2025.8.3",
                "exclude_database": False,
                "size": 0.0  # Uppdateras senare med faktisk storlek
            },
            "repositories": [],
            "folders": ["homeassistant"],
            "compressed": True,
            "protected": False,
            "crypto": None,
            "docker": {
                "registries": {},
                "mtu": None,
                "enable_ipv6": None
            }
        }
    
    def copy_gridenforcer_integration(self, target_dir: Path) -> bool:
        """Kopiera GridEnforcer integration (custom_components/gridenforcer)"""
        
        if not self.integration_path.exists():
            print(f"❌ Integration hittades inte: {self.integration_path}")
            return False
        
        target_integration = target_dir / "custom_components" / "gridenforcer"
        target_integration.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            print(f"📁 Kopierar integration: {self.integration_path} → {target_integration}")
            
            # Filter för att skippa onödiga filer
            def should_ignore(src_dir, names):
                ignored = []
                for name in names:
                    if (name == '__pycache__' or 
                        name.endswith('.pyc') or 
                        name.endswith('.pyo') or
                        name.startswith('.') or
                        name.endswith('~')):
                        ignored.append(name)
                return ignored
            
            shutil.copytree(self.integration_path, target_integration, ignore=should_ignore)
            
            # Verifiera viktiga filer
            required_files = ["__init__.py", "manifest.json"]
            for file in required_files:
                if not (target_integration / file).exists():
                    print(f"❌ Saknar kritisk fil: {file}")
                    return False
            
            file_count = len(list(target_integration.rglob("*")))
            print(f"✅ Integration kopierad: {file_count} filer")
            return True
            
        except Exception as e:
            print(f"❌ Fel vid kopiering av integration: {e}")
            return False
    
    def copy_gridenforcer_packages(self, target_dir: Path) -> bool:
        """Kopiera GridEnforcer packages-konfiguration"""
        
        if not self.packages_path.exists():
            print(f"⚠️  Packages hittades inte: {self.packages_path} (skippar)")
            return True  # Inte kritiskt
        
        target_packages = target_dir / "packages" / "gridenforcer"
        target_packages.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            print(f"📦 Kopierar packages: {self.packages_path} → {target_packages}")
            
            def should_ignore_yaml(src_dir, names):
                ignored = []
                for name in names:
                    if (name.startswith('.') or 
                        name.endswith('~') or 
                        name.endswith('.tmp')):
                        ignored.append(name)
                return ignored
            
            shutil.copytree(self.packages_path, target_packages, ignore=should_ignore_yaml)
            
            yaml_files = list(target_packages.rglob("*.yaml")) + list(target_packages.rglob("*.yml"))
            print(f"✅ Packages kopierad: {len(yaml_files)} YAML-filer")
            return True
            
        except Exception as e:
            print(f"⚠️  Fel vid packages-kopiering: {e} (fortsätter)")
            return True  # Inte kritiskt
    
    def create_basic_ha_config(self, target_dir: Path, version: str) -> None:
        """Skapa grundläggande HA konfigurationsfiler"""
        
        print("📝 Skapar grundläggande HA-konfiguration")
        
        # configuration.yaml
        config = {
            "default_config": None,
            "homeassistant": {
                "name": "GridEnforcer System",
                "latitude": 57.7089,
                "longitude": 11.9746,
                "elevation": 12,
                "unit_system": "metric",
                "time_zone": "Europe/Stockholm",
                "currency": "SEK",
                "country": "SE"
            }
        }
        
        with open(target_dir / "configuration.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        # secrets.yaml (template)
        secrets = {
            "# GridEnforcer Secrets Template": "Fyll i för din installation",
            "mqtt_password": "CHANGE_ME",
            "flower_mqtt_broker": "YOUR_BROKER.com",
            "flower_mqtt_username": "YOUR_USERNAME", 
            "flower_mqtt_password": "YOUR_PASSWORD",
            "solax1_ip": "192.168.1.100",
            "solax2_ip": "192.168.1.101",
            "solax3_ip": "192.168.1.102"
        }
        
        with open(target_dir / "secrets.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(secrets, f, default_flow_style=False, allow_unicode=True)
        
        # automations.yaml (minimal)
        automations = [{
            "id": "gridenforcer_welcome",
            "alias": "GridEnforcer Welcome",
            "trigger": {"platform": "homeassistant", "event": "start"},
            "action": {
                "service": "persistent_notification.create",
                "data": {
                    "title": "GridEnforcer Installation",
                    "message": f"GridEnforcer {version} har installerats. Konfigurera via Integrations.",
                    "notification_id": "gridenforcer_installed"
                }
            }
        }]
        
        with open(target_dir / "automations.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(automations, f, default_flow_style=False, allow_unicode=True)
        
        print("✅ HA-konfiguration skapad")
    
    def add_verification_script(self, target_dir: Path, version: str) -> None:
        """Lägg till post-deployment verification script"""
        
        python_scripts_dir = target_dir / "python_scripts"
        python_scripts_dir.mkdir(exist_ok=True)
        
        # Använd template om den finns, annars skapa enkel version
        template_file = self.templates_path / "post_deployment_verify.py"
        
        if template_file.exists():
            print("📄 Kopierar verification script från template")
            content = template_file.read_text(encoding='utf-8')
            content = content.replace("{{VERSION}}", version)
        else:
            print("📄 Skapar enkel verification script")
            content = f'''"""GridEnforcer {version} Post-Deployment Verification"""

import logging
_LOGGER = logging.getLogger(__name__)

hass = data.get("hass")
if hass:
    # Skapa notification
    hass.services.call("persistent_notification", "create", {{
        "title": "GridEnforcer {version} Verification",
        "message": "Post-deployment verification kördes. Kontrollera att integration fungerar.",
        "notification_id": "gridenforcer_verify"
    }})
    
    _LOGGER.info("GridEnforcer {version} verification completed")
'''
        
        with open(python_scripts_dir / "gridenforcer_verify.py", 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Verification script tillagd")
    
    def create_homeassistant_tar_gz(self, ha_content_dir: Path, temp_dir: Path) -> Path:
        """Skapa homeassistant.tar.gz från HA content"""
        
        print("🗜️  Skapar homeassistant.tar.gz...")
        
        ha_tar_path = temp_dir / "homeassistant.tar.gz"
        
        with tarfile.open(ha_tar_path, "w:gz") as tar:
            for file_path in ha_content_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(ha_content_dir)
                    tar.add(file_path, arcname=str(arcname))
        
        size_mb = ha_tar_path.stat().st_size / 1024 / 1024
        print(f"✅ homeassistant.tar.gz skapad: {size_mb:.1f} MB")
        
        return ha_tar_path
    
    def create_final_backup_tar(self, temp_dir: Path, version: str, output_dir: Path, ha_tar_path: Path, metadata: Dict) -> Path:
        """Skapa slutgiltig backup.tar fil"""
        
        backup_name = f"gridenforcer-{version}-{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar"
        backup_file = output_dir / backup_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📦 Skapar slutgiltig backup: {backup_file}")
        
        # Uppdatera metadata med faktisk storlek
        ha_size_mb = ha_tar_path.stat().st_size / 1024 / 1024
        metadata["homeassistant"]["size"] = round(ha_size_mb, 1)
        
        # Skapa backup.json
        backup_json_path = temp_dir / "backup.json"
        with open(backup_json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Skapa slutgiltig .tar fil (INTE .tar.gz)
        with tarfile.open(backup_file, "w") as tar:
            # Lägg till backup.json
            tar.add(backup_json_path, arcname="./backup.json")
            # Lägg till homeassistant.tar.gz
            tar.add(ha_tar_path, arcname="homeassistant.tar.gz")
        
        file_size_mb = backup_file.stat().st_size / 1024 / 1024
        print(f"✅ Backup skapad: {backup_file} ({file_size_mb:.1f} MB)")
        
        # Visa struktur för verifiering
        print("📋 Backup innehåll:")
        with tarfile.open(backup_file, "r") as verify_tar:
            for member in verify_tar.getmembers():
                size_kb = member.size // 1024
                print(f"   - {member.name} ({size_kb} KB)")
        
        return backup_file
    
    def create_backup(self, version: str, output_dir: Path, manifest_file: Optional[Path] = None) -> Path:
        """Huvudfunktion - skapa komplett GridEnforcer backup"""
        
        print(f"🚀 Skapar GridEnforcer backup för version {version}")
        print("=" * 60)
        
        # Ladda manifest om tillgängligt
        manifest = None
        if manifest_file and manifest_file.exists():
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            deployment_type = manifest.get("gridenforcer", {}).get("deployment_type", "unknown")
            print(f"📋 Använder manifest: deployment_type = {deployment_type}")
        else:
            deployment_type = "manual_deployment"
            print("📋 Inget manifest tillgängligt")
        
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            ha_content_dir = temp_dir / "ha_content"
            ha_content_dir.mkdir()
            
            print(f"🗂️  Arbetar i: {temp_dir}")
            
            # 1. Skapa HA backup metadata
            metadata = self.create_ha_backup_metadata(version, deployment_type)
            
            # 2. Kopiera GridEnforcer integration
            if not self.copy_gridenforcer_integration(ha_content_dir):
                raise RuntimeError("Integration kopiering misslyckades")
            
            # 3. Kopiera packages-konfiguration
            self.copy_gridenforcer_packages(ha_content_dir)
            
            # 4. Skapa grundläggande HA-konfiguration
            self.create_basic_ha_config(ha_content_dir, version)
            
            # 5. Lägg till verification script
            self.add_verification_script(ha_content_dir, version)
            
            # 6. Skapa homeassistant.tar.gz
            ha_tar_path = self.create_homeassistant_tar_gz(ha_content_dir, temp_dir)
            
            # 7. Skapa slutgiltig backup.tar
            backup_file = self.create_final_backup_tar(temp_dir, version, output_dir, ha_tar_path, metadata)
            
            print("=" * 60)
            print("🎉 GridEnforcer backup skapad framgångsrikt!")
            
            return backup_file


def main():
    # 🚨 DEBUG: Uncomment för lokal debugging  
    # import sys
    # sys.argv = ['script', '--version', 'v0.1.0', '--output-dir', 'deployment']
    
    parser = argparse.ArgumentParser(
        description="Skapa GridEnforcer backup för Home Assistant deployment"
    )
    parser.add_argument(
        "--version",
        required=True,
        help="GridEnforcer version (t.ex. v0.1.0)"
    )
    parser.add_argument(
        "--output-dir", 
        type=Path,
        default=Path("deployment"),
        help="Output directory för backup (default: deployment/)"
    )
    parser.add_argument(
        "--manifest-file",
        type=Path,
        help="Path till deployment manifest (valfritt)"
    )
    
    args = parser.parse_args()
    
    try:
        creator = GridEnforcerBackupCreator()
        
        backup_file = creator.create_backup(
            args.version,
            args.output_dir,
            args.manifest_file
        )
        
        print(f"\n🎯 Deployment-instruktioner:")
        print(f"1. Överför {backup_file.name} till din Home Assistant enhet")
        print(f"2. Gå till Settings > System > Backups")  
        print(f"3. Klicka på '+' och välj 'Upload backup'")
        print(f"4. Välj backup-filen och klicka 'Upload'")
        print(f"5. Klicka 'Restore' på den uppladdade backup-filen")
        print(f"6. Starta om Home Assistant efter restore")
        print(f"7. Konfigurera GridEnforcer via Settings > Integrations")
        print(f"8. Kör python_scripts.gridenforcer_verify för verifiering")
        
        # CI/CD output
        print(f"\n::set-output name=backup_file::{backup_file}")
        print(f"::set-output name=backup_size::{backup_file.stat().st_size}")
        
    except Exception as e:
        print(f"❌ Backup creation misslyckades: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()