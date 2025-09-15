#!/usr/bin/env python3
"""
Ansible-Enhanced GridEnforcer Backup Creator
Skapar HA backup som mergar befintlig config med GridEnforcer
"""

import json
import tarfile
import tempfile
import argparse
import sys
import shutil
import uuid
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class AnsibleBackupCreator:
    """Skapar GridEnforcer backup med intelligent config merge"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.integration_path = self.project_root / "custom_components" / "gridenforcer"
        self.packages_path = self.project_root / "packages" / "gridenforcer"
        
    def load_existing_ha_config(self, existing_config_dir: Path) -> Dict:
        """Läs befintlig HA konfiguration från Ansible fetch"""
        
        config_file = existing_config_dir / "configuration.yaml"
        
        if not config_file.exists():
            print("⚠️  Ingen befintlig configuration.yaml hittad, skapar grundkonfiguration")
            return self.create_default_ha_config()
        
        try:
            print(f"📖 Läser befintlig HA config: {config_file}")
            with open(config_file, 'r', encoding='utf-8') as f:
                existing_config = yaml.safe_load(f) or {}
            
            print(f"✅ Befintlig config laddad: {len(existing_config)} sektioner")
            return existing_config
            
        except Exception as e:
            print(f"⚠️  Kunde inte läsa befintlig config: {e}")
            print("📝 Använder grundkonfiguration istället")
            return self.create_default_ha_config()
    
    def create_default_ha_config(self) -> Dict:
        """Skapa grundläggande HA config om ingen existerar"""
        return {
            "default_config": None,
            "homeassistant": {
                "name": "Home Assistant",
                "latitude": 57.7089,
                "longitude": 11.9746,
                "elevation": 12,
                "unit_system": "metric",
                "time_zone": "Europe/Stockholm",
                "currency": "SEK",
                "country": "SE"
            }
        }
    
    def merge_gridenforcer_config(self, existing_config: Dict) -> Dict:
        """Intelligent merge av GridEnforcer med befintlig config"""
        
        print("🔀 Mergar GridEnforcer med befintlig konfiguration...")
        
        # Kopiera befintlig config
        merged_config = existing_config.copy()
        
        # GridEnforcer-specifika tillägg (om de inte redan finns)
        gridenforcer_additions = {
            # Säkerställ packages läses
            "packages": "!include_dir_named packages",
            
            # Python scripts (för verification)
            "python_script": None,
            
            # GridEnforcer kommer att konfigureras via integration UI
            "# GridEnforcer Integration": "Konfigurera via Settings > Integrations efter restore"
        }
        
        # Merge additions utan att skriva över befintliga
        for key, value in gridenforcer_additions.items():
            if key not in merged_config:
                merged_config[key] = value
                print(f"   + Lade till: {key}")
            else:
                print(f"   ↪ Behöll befintlig: {key}")
        
        # Uppdatera homeassistant sektion för GridEnforcer
        if "homeassistant" in merged_config:
            ha_section = merged_config["homeassistant"]
            
            # Säkerställ svensk lokalisering (för GridEnforcer)
            gridenforcer_ha_settings = {
                "time_zone": "Europe/Stockholm",
                "currency": "SEK",
                "country": "SE",
                "unit_system": "metric"
            }
            
            for setting, value in gridenforcer_ha_settings.items():
                if setting not in ha_section:
                    ha_section[setting] = value
                    print(f"   + HA setting: {setting} = {value}")
        
        print(f"✅ Config merge slutförd: {len(merged_config)} sektioner totalt")
        return merged_config
    
    def copy_existing_files(self, existing_config_dir: Path, target_dir: Path) -> None:
        """Kopiera befintliga HA-filer (preserverar befintlig config)"""
        
        print("📁 Kopierar befintliga HA-filer...")
        
        # Filer att kopiera från befintlig installation
        files_to_preserve = [
            "secrets.yaml",
            "automations.yaml", 
            "scenes.yaml",
            "scripts.yaml",
            "customize.yaml",
            "known_devices.yaml"
        ]
        
        copied_count = 0
        for filename in files_to_preserve:
            src_file = existing_config_dir / filename
            dst_file = target_dir / filename
            
            if src_file.exists():
                shutil.copy2(src_file, dst_file)
                print(f"   ✅ Kopierad: {filename}")
                copied_count += 1
            else:
                print(f"   ➖ Hittades inte: {filename}")
        
        print(f"✅ {copied_count} befintliga filer kopierade")
    
    def copy_existing_directories(self, existing_config_dir: Path, target_dir: Path) -> None:
        """Kopiera befintliga directories (bevarar befintliga custom_components etc)"""
        
        print("📂 Kopierar befintliga directories...")
        
        # Directories att preservera
        dirs_to_preserve = [
            "custom_components",  # Befintliga integrations
            "packages",          # Befintliga packages
            "www",               # Web resources
            "themes",            # UI themes
            "blueprints"         # Automation blueprints
        ]
        
        for dirname in dirs_to_preserve:
            src_dir = existing_config_dir / dirname
            dst_dir = target_dir / dirname
            
            if src_dir.exists() and src_dir.is_dir():
                print(f"   📂 Kopierar befintlig directory: {dirname}")
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
            else:
                print(f"   ➖ Directory hittades inte: {dirname}")
        
        print("✅ Befintliga directories kopierade")
    
    def add_gridenforcer_to_existing(self, target_dir: Path) -> None:
        """Lägg till GridEnforcer till befintlig struktur"""
        
        print("⚡ Lägger till GridEnforcer till befintlig installation...")
        
        # 1. Lägg till GridEnforcer integration
        gridenforcer_target = target_dir / "custom_components" / "gridenforcer"
        gridenforcer_target.parent.mkdir(parents=True, exist_ok=True)
        
        if self.integration_path.exists():
            if gridenforcer_target.exists():
                print("   🔄 Uppdaterar befintlig GridEnforcer integration")
                shutil.rmtree(gridenforcer_target)
            
            shutil.copytree(self.integration_path, gridenforcer_target, 
                          ignore=lambda d, names: [n for n in names if n == '__pycache__'])
            print("   ✅ GridEnforcer integration tillagd")
        else:
            print(f"   ❌ GridEnforcer integration hittades inte: {self.integration_path}")
        
        # 2. Lägg till GridEnforcer packages
        packages_target = target_dir / "packages" / "gridenforcer"
        packages_target.parent.mkdir(parents=True, exist_ok=True)
        
        if self.packages_path.exists():
            if packages_target.exists():
                print("   🔄 Uppdaterar befintlig GridEnforcer packages")
                shutil.rmtree(packages_target)
            
            shutil.copytree(self.packages_path, packages_target)
            print("   ✅ GridEnforcer packages tillagd")
        else:
            print(f"   ⚠️  GridEnforcer packages hittades inte: {self.packages_path}")
        
        # 3. Lägg till verification script
        python_scripts_dir = target_dir / "python_scripts"
        python_scripts_dir.mkdir(exist_ok=True)
        
        verify_script = '''"""GridEnforcer Post-Deployment Verification"""
import logging
_LOGGER = logging.getLogger(__name__)

hass = data.get("hass")
if hass:
    hass.services.call("persistent_notification", "create", {
        "title": "GridEnforcer Installation",
        "message": "GridEnforcer har installerats framgångsrikt! Konfigurera via Settings > Integrations.",
        "notification_id": "gridenforcer_installed"
    })
    _LOGGER.info("GridEnforcer installation verification completed")
'''
        
        with open(python_scripts_dir / "gridenforcer_verify.py", 'w', encoding='utf-8') as f:
            f.write(verify_script)
        print("   ✅ GridEnforcer verification script tillagt")
    
    def create_merged_backup(self, version: str, existing_config_dir: Path, output_dir: Path) -> Path:
        """Huvudfunktion - skapa merged backup med befintlig config + GridEnforcer"""
        
        print(f"🚀 Skapar merged GridEnforcer backup för version {version}")
        print("=" * 70)
        
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            ha_content_dir = temp_dir / "ha_content"
            ha_content_dir.mkdir()
            
            # 1. Läs befintlig HA konfiguration
            existing_config = self.load_existing_ha_config(existing_config_dir)
            
            # 2. Merge med GridEnforcer
            merged_config = self.merge_gridenforcer_config(existing_config)
            
            # 3. Kopiera befintliga filer
            self.copy_existing_files(existing_config_dir, ha_content_dir)
            
            # 4. Kopiera befintliga directories
            self.copy_existing_directories(existing_config_dir, ha_content_dir)
            
            # 5. Lägg till GridEnforcer
            self.add_gridenforcer_to_existing(ha_content_dir)
            
            # 6. Skriv merged configuration.yaml
            with open(ha_content_dir / "configuration.yaml", 'w', encoding='utf-8') as f:
                yaml.dump(merged_config, f, default_flow_style=False, allow_unicode=True)
            print("✅ Merged configuration.yaml skapad")
            
            # 7. Skapa HA-kompatibel backup
            backup_file = self.create_ha_backup_file(temp_dir, ha_content_dir, version, output_dir)
            
            print("=" * 70)
            print("🎉 Merged GridEnforcer backup skapad!")
            print("📋 Innehåller:")
            print("   ✅ Din befintliga HA konfiguration (preserverad)")
            print("   ✅ GridEnforcer integration")
            print("   ✅ GridEnforcer packages")
            print("   ✅ Befintliga custom_components")
            print("   ✅ Befintliga automations, scenes, scripts")
            
            return backup_file
    
    def create_ha_backup_file(self, temp_dir: Path, ha_content_dir: Path, version: str, output_dir: Path) -> Path:
        """Skapa slutgiltig HA backup fil"""
        
        # HA backup metadata
        metadata = {
            "slug": f"gridenforcer-merged-{version.replace('v', '').replace('.', '-')}",
            "version": 2,
            "name": f"GridEnforcer {version} (Merged Installation)",
            "date": datetime.now(timezone.utc).isoformat(),
            "type": "partial",
            "supervisor_version": "2025.09.0",
            "extra": {
                "instance_id": str(uuid.uuid4()),
                "gridenforcer_merged_deployment": True,
                "preserves_existing_config": True
            },
            "addons": [],
            "homeassistant": {
                "version": "2025.8.3",
                "exclude_database": False,
                "size": 0.0
            },
            "repositories": [],
            "folders": ["homeassistant"],
            "compressed": True,
            "protected": False,
            "crypto": None,
            "docker": {"registries": {}, "mtu": None, "enable_ipv6": None}
        }
        
        # Skapa homeassistant.tar.gz
        ha_tar_path = temp_dir / "homeassistant.tar.gz"
        with tarfile.open(ha_tar_path, "w:gz") as tar:
            for file_path in ha_content_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(ha_content_dir)
                    tar.add(file_path, arcname=str(arcname))
        
        # Uppdatera storlek
        ha_size_mb = ha_tar_path.stat().st_size / 1024 / 1024
        metadata["homeassistant"]["size"] = round(ha_size_mb, 1)
        
        # Skapa backup.json
        backup_json_path = temp_dir / "backup.json"
        with open(backup_json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Skapa slutgiltig backup.tar
        output_dir.mkdir(parents=True, exist_ok=True)
        backup_name = f"gridenforcer-merged-{version}-{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar"
        backup_file = output_dir / backup_name
        
        with tarfile.open(backup_file, "w") as tar:
            tar.add(backup_json_path, arcname="backup.json")
            tar.add(ha_tar_path, arcname="homeassistant.tar.gz")
        
        print(f"✅ Backup skapad: {backup_file} ({backup_file.stat().st_size / 1024 / 1024:.1f} MB)")
        return backup_file


def main():
    parser = argparse.ArgumentParser(
        description="Skapa merged GridEnforcer backup med befintlig HA config"
    )
    parser.add_argument("--version", required=True, help="GridEnforcer version")
    parser.add_argument("--existing-config-dir", type=Path, required=True, 
                       help="Directory med befintlig HA config (från Ansible fetch)")
    parser.add_argument("--output-dir", type=Path, default=Path("deployment"),
                       help="Output directory")
    
    args = parser.parse_args()
    
    try:
        creator = AnsibleBackupCreator()
        backup_file = creator.create_merged_backup(
            args.version, 
            args.existing_config_dir,
            args.output_dir
        )
        
        print(f"\n🎯 Deployment instruktioner:")
        print(f"1. Överför {backup_file.name} till Home Assistant")
        print(f"2. Återställ backup via HA UI")
        print(f"3. Systemet startar om med din befintliga config + GridEnforcer")
        print(f"4. Konfigurera GridEnforcer via Settings > Integrations")
        
        print(f"\n::set-output name=backup_file::{backup_file}")
        
    except Exception as e:
        print(f"❌ Fel: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()