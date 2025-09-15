#!/usr/bin/env python3
"""
GridEnforcer Deployment Manifest Creator
Skapar deployment-manifest för CI/CD pipeline
"""


import json
import yaml
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 🚨 DEBUG: Uncomment för lokal debugging
sys.argv = ['script', '--version', 'v0.1.1', '--output-dir', 'deployment']

class DeploymentManifestCreator:
    """Skapar deployment-manifest för GridEnforcer releases"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.integration_path = self.project_root / "custom_components" / "gridenforcer"
        self.specs_dir = self.project_root / "deployment-specs"
        
    def get_git_info(self) -> Dict[str, str]:
        """Hämta git-information för aktuell commit"""
        try:
            # Hämta aktuell commit hash
            commit_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], 
                cwd=self.project_root,
                text=True
            ).strip()
            
            # Hämta aktuell branch
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.project_root, 
                text=True
            ).strip()
            
            # Försök hämta senaste tag
            try:
                latest_tag = subprocess.check_output(
                    ["git", "describe", "--tags", "--abbrev=0"],
                    cwd=self.project_root,
                    text=True
                ).strip()
            except subprocess.CalledProcessError:
                latest_tag = "untagged"
            
            return {
                "commit_hash": commit_hash[:8],  # Kort hash
                "branch": branch,
                "latest_tag": latest_tag,
                "repository": self.get_repository_url()
            }
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Git-kommando misslyckades: {e}")
            return {
                "commit_hash": "unknown",
                "branch": "unknown", 
                "latest_tag": "unknown",
                "repository": "unknown"
            }
    
    def get_repository_url(self) -> str:
        """Hämta repository URL från git"""
        try:
            remote_url = subprocess.check_output(
                ["git", "remote", "get-url", "origin"],
                cwd=self.project_root,
                text=True
            ).strip()
            
            # Konvertera SSH till HTTPS format för bättre kompatibilitet
            if remote_url.startswith("git@github.com:"):
                remote_url = remote_url.replace("git@github.com:", "https://github.com/")
            if remote_url.endswith(".git"):
                remote_url = remote_url[:-4]
                
            return remote_url
        except subprocess.CalledProcessError:
            return "https://github.com/unknown/unknown"
    
    def load_version_spec(self, version: str) -> Dict[str, any]: # pyright: ignore[reportGeneralTypeIssues]
        """
        Ladda versionsspecifikation från YAML-fil
        Fallback till default om fil inte existerar
        """
        spec_file = self.specs_dir / f"{version}.yaml"
        
        if spec_file.exists():
            print(f"📄 Laddar versionsspec från {spec_file}")
            try:
                with open(spec_file, 'r', encoding='utf-8') as f:
                    spec = yaml.safe_load(f)
                    return self.validate_spec(spec, version)
            except yaml.YAMLError as e:
                print(f"⚠️  YAML-fel i {spec_file}: {e}")
                print("📝 Använder fallback-spec")
        else:
            print(f"📄 Versionsspec {spec_file} hittades inte, skapar default")
        
        return self.create_default_spec(version)
    
    def validate_spec(self, spec: Dict, version: str) -> Dict[str, any]: # pyright: ignore[reportGeneralTypeIssues]
        """Validera och komplettera versionsspec"""
        
        # Kontrollera obligatoriska fält
        required_fields = ["version", "deployment_type"]
        for field in required_fields:
            if field not in spec:
                print(f"⚠️  Saknar obligatoriskt fält '{field}' i spec, använder default")
                return self.create_default_spec(version)
        
        # Sätt default-värden för optional fält
        defaults = {
            "breaking_changes": False,
            "requires_restart": True,
            "changes": {
                "integration_files": [],
                "config_changes": [],
                "new_features": [],
                "bug_fixes": [],
                "migration_notes": []
            },
            "dependencies": {
                "addons_required": [],
                "integrations_required": [],
                "python_packages": []
            }
        }
        
        # Merge defaults med spec
        for key, default_value in defaults.items():
            if key not in spec:
                spec[key] = default_value
            elif isinstance(default_value, dict):
                for subkey, subdefault in default_value.items():
                    if subkey not in spec[key]:
                        spec[key][subkey] = subdefault
        
        return spec
    
    def create_default_spec(self, version: str) -> Dict[str, any]: # pyright: ignore[reportGeneralTypeIssues]
        """Skapa default versionsspec när YAML-fil saknas"""
        
        # Försök hitta föregående version från git tags
        previous_version = self.find_previous_version(version)
        
        is_initial = previous_version is None
        
        return {
            "version": version,
            "previous_version": previous_version,
            "deployment_type": "initial_install" if is_initial else "patch_update",
            "breaking_changes": False,
            "requires_restart": True,
            "changes": {
                "integration_files": ["all"] if is_initial else [],
                "config_changes": ["initial_configuration"] if is_initial else [],
                "new_features": ["GridEnforcer Energy Management System"] if is_initial else [],
                "bug_fixes": [],
                "migration_notes": [
                    "Första installation av GridEnforcer" if is_initial 
                    else f"Uppdatering från {previous_version} till {version}"
                ]
            },
            "dependencies": {
                "addons_required": [
                    {
                        "slug": "core_mosquitto",
                        "name": "Mosquitto Broker", 
                        "min_version": "6.2.1",
                        "required": True,
                        "purpose": "FCR-D kommunikation med Flower aggregator"
                    }
                ],
                "integrations_required": [
                    {
                        "domain": "nordpool",
                        "source": "hacs",
                        "required": True,
                        "purpose": "Svenska elpriser för optimering"
                    },
                    {
                        "domain": "modbus", 
                        "source": "core",
                        "required": True,
                        "purpose": "Kommunikation med Solax växelriktare"
                    }
                ],
                "python_packages": [
                    {"name": "numpy", "min_version": "1.21.0"},
                    {"name": "scipy", "min_version": "1.7.0"}
                ]
            }
        }
    
    def find_previous_version(self, current_version: str) -> Optional[str]:
        """Hitta föregående version från git tags"""
        try:
            all_tags = subprocess.check_output(
                ["git", "tag", "-l", "--sort=-version:refname"],
                cwd=self.project_root,
                text=True
            ).strip().split('\n')
            
            # Hitta föregående version
            current_found = False
            for tag in all_tags:
                if not tag:  # Skippa tomma rader
                    continue
                if tag == current_version:
                    current_found = True
                    continue
                if current_found:
                    return tag
                    
        except subprocess.CalledProcessError:
            pass
            
        return None
    
    def get_required_dependencies(self, spec: Dict) -> Dict[str, List[Dict]]:
        """Hämta beroenden från versionsspec eller använd defaults"""
        
        spec_deps = spec.get("dependencies", {})
        
        return {
            "home_assistant_addons": spec_deps.get("addons_required", [
                {
                    "slug": "core_mosquitto",
                    "name": "Mosquitto Broker",
                    "min_version": "6.2.1",
                    "required": True,
                    "config_required": {
                        "logins": "gridenforcer user account",
                        "anonymous": False
                    }
                },
                {
                    "slug": "core_ssh",
                    "name": "Terminal & SSH",
                    "min_version": "9.6.0", 
                    "required": False,
                    "purpose": "Automated deployment via SSH"
                }
            ]),
            "home_assistant_integrations": spec_deps.get("integrations_required", [
                {
                    "domain": "nordpool",
                    "source": "hacs",
                    "required": True,
                    "purpose": "Electricity price data for Sweden"
                },
                {
                    "domain": "modbus",
                    "source": "core",
                    "required": True,
                    "purpose": "Communication with Solax inverters"
                }
            ]),
            "python_packages": spec_deps.get("python_packages", [
                {
                    "name": "numpy",
                    "min_version": "1.21.0",
                    "purpose": "Price calculation algorithms"
                },
                {
                    "name": "scipy", 
                    "min_version": "1.7.0",
                    "purpose": "Advanced price optimization"
                }
            ])
        }
    
    def create_deployment_instructions(self, deployment_type: str) -> Dict[str, List[str]]:
        """Skapa deployment-instruktioner för olika scenarios"""
        
        base_manual_steps = [
            "1. Kontrollera att alla nödvändiga addons är installerade",
            "2. Ladda upp GridEnforcer backup-fil till Home Assistant",
            "3. Återställ backup via Settings > System > Backups",
            "4. Starta om Home Assistant", 
            "5. Verifiera att GridEnforcer integration har laddats korrekt"
        ]
        
        base_automated_steps = [
            "1. Kör: ./deploy-gridenforcer.sh --target-host [IP_ADDRESS]",
            "2. Följ instruktionerna från deployment-scriptet",
            "3. Verifiera deployment via Home Assistant UI"
        ]
        
        if deployment_type == "initial_install":
            manual_steps = [
                "FÖRSTA INSTALLATION:",
                "1. Installera Mosquitto Broker addon",
                "2. Konfigurera MQTT med gridenforcer användarnamn",
                "3. Installera Nord Pool integration via HACS",
                "4. Installera Modbus integration (oftast redan installerat)",
            ] + base_manual_steps + [
                "6. Konfigurera GridEnforcer via Integrations > Add Integration"
            ]
            
            automated_steps = [
                "FÖRSTA INSTALLATION:",
                "1. SSH-åtkomst till Home Assistant krävs",
                "2. Kör: ./deploy-gridenforcer.sh --target-host [IP] --initial-install",
                "3. Följ konfigurationsguiden för enhetsinställningar"
            ]
        else:
            manual_steps = ["UPPDATERING:"] + base_manual_steps
            automated_steps = ["UPPDATERING:"] + base_automated_steps
        
        return {
            "manual_deployment": manual_steps,
            "automated_deployment": automated_steps,
            "post_deployment_verification": [
                "Kontrollera att sensor.gridenforcer_inverter_mode existerar",
                "Verifiera att number.gridenforcer_soc_backup är konfigurerbar",
                "Testa att select.gridenforcer_operation_mode fungerar",
                "Kontrollera loggar för eventuella fel"
            ]
        }
    
    def create_manifest(self, version: str, output_dir: Path, build_info: Optional[Dict] = None) -> Path:
        """Skapa komplett deployment-manifest"""
        
        print(f"🏗️  Skapar deployment-manifest för version {version}...")
        
        # Samla all information
        git_info = self.get_git_info()
        version_spec = self.load_version_spec(version)
        dependencies = self.get_required_dependencies(version_spec)
        instructions = self.create_deployment_instructions(version_spec["deployment_type"])
        
        # Bygg manifest
        manifest = {
            "manifest_version": "1.0",
            "created_at": datetime.now().isoformat(),
            "gridenforcer": {
                "version": version,
                "deployment_type": version_spec["deployment_type"],
                "previous_version": version_spec.get("previous_version"),
                "breaking_changes": version_spec["breaking_changes"],
                "requires_restart": version_spec["requires_restart"]
            },
            "git_info": git_info,
            "build_info": build_info or {
                "build_system": "local",
                "build_time": datetime.now().isoformat()
            },
            "changes": version_spec["changes"],
            "dependencies": dependencies,
            "deployment": {
                "instructions": instructions,
                "estimated_deployment_time": "5-10 minuter för uppdatering, 15-30 minuter för första installation",
                "backup_size_estimate": "2-5 MB",
                "rollback_supported": True
            },
            "compatibility": {
                "home_assistant_min_version": "2023.12.0",
                "python_min_version": "3.11",
                "supported_architectures": ["amd64", "arm64"]
            }
        }
        
        # Skapa output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Skriv manifest-fil
        manifest_file = output_dir / f"deployment-manifest-{version}.json"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Deployment-manifest skapad: {manifest_file}")
        print(f"📝 Deployment-typ: {version_spec['deployment_type']}")
        print(f"🔄 Föregående version: {version_spec.get('previous_version', 'Ingen')}")
        
        return manifest_file


def main():
    parser = argparse.ArgumentParser(
        description="Skapa GridEnforcer deployment-manifest"
    )
    parser.add_argument(
        "--version", 
        required=True,
        help="GridEnforcer version (t.ex. v0.1.0 eller auto för git tag)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("deployment"),
        help="Output directory för manifest (default: deployment/)"
    )
    parser.add_argument(
        "--build-number",
        help="CI build number (valfritt)"
    )
    parser.add_argument(
        "--ci-system",
        help="CI system namn (t.ex. github_actions)"
    )
    
    args = parser.parse_args()
    
    # Hantera auto-version detection
    version = args.version
    if version == "auto":
        try:
            version = subprocess.check_output(
                ["git", "describe", "--tags", "--exact-match"],
                text=True
            ).strip()
            print(f"🔍 Auto-detekterad version: {version}")
        except subprocess.CalledProcessError:
            print("❌ Kunde inte auto-detektera version från git tags")
            print("💡 Använd --version med explicit version eller skapa en git tag först")
            sys.exit(1)
    
    # Build info från CI environment
    build_info = {
        "build_system": args.ci_system or "local",
        "build_number": args.build_number,
        "build_time": datetime.now().isoformat()
    }
    
    # Skapa manifest
    creator = DeploymentManifestCreator()
    
    try:
        manifest_file = creator.create_manifest(version, args.output_dir, build_info)
        
        print("\n🎉 Deployment-manifest framgångsrikt skapad!")
        print(f"📁 Fil: {manifest_file}")
        print(f"📦 Storlek: {manifest_file.stat().st_size} bytes")
        
        # Output för CI/CD systems
        if args.ci_system:
            print(f"::set-output name=manifest_file::{manifest_file}")
            print(f"::set-output name=version::{version}")
        
    except Exception as e:
        print(f"❌ Misslyckades att skapa deployment-manifest: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()