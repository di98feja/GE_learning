#!/usr/bin/env python3
"""
GridEnforcer Deployment Artifacts Creator
Orchestrator som skapar både manifest och backup för komplett deployment
"""

import subprocess
import argparse
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class DeploymentArtifactsCreator:
    """Orchestrator för att skapa alla deployment-artefakter"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.scripts_dir = self.project_root / "scripts"
        
    def run_script(self, script_name: str, args: List[str]) -> Dict[str, any]: # pyright: ignore[reportGeneralTypeIssues]
        """Kör ett Python-script och returnera resultat"""
        
        script_path = self.scripts_dir / script_name
        
        if not script_path.exists():
            raise FileNotFoundError(f"Script hittades inte: {script_path}")
        
        print(f"🔧 Kör {script_name} med args: {' '.join(args)}")
        
        # Bygg kommando
        cmd = [sys.executable, str(script_path)] + args
        
        try:
            # Kör script och fanga output
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Script {script_name} misslyckades: {result.stderr}")
            
            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except subprocess.SubprocessError as e:
            raise RuntimeError(f"Kunde inte köra {script_name}: {e}")
    
    def parse_script_output(self, stdout: str) -> Dict[str, str]:
        """Parsa CI/CD output från script (::set-output format)"""
        
        outputs = {}
        
        for line in stdout.split('\n'):
            line = line.strip()
            if line.startswith('::set-output name='):
                # Format: ::set-output name=key::value
                try:
                    parts = line.replace('::set-output name=', '').split('::')
                    if len(parts) >= 2:
                        key = parts[0]
                        value = '::'.join(parts[1:])  # Hantera :: i värden
                        outputs[key] = value
                except Exception:
                    continue  # Skippa malformade output-rader
        
        return outputs
    
    def create_manifest(self, version: str, output_dir: Path, build_info: Dict) -> Path:
        """Skapa deployment manifest"""
        
        print("📋 Skapar deployment manifest...")
        
        manifest_args = [
            "--version", version,
            "--output-dir", str(output_dir)
        ]
        
        # Lägg till build info
        if build_info.get("build_number"):
            manifest_args.extend(["--build-number", build_info["build_number"]])
        if build_info.get("ci_system"):
            manifest_args.extend(["--ci-system", build_info["ci_system"]])
        
        result = self.run_script("create_deployment_manifest.py", manifest_args)
        
        # Parsa output för manifest fil path
        outputs = self.parse_script_output(result["stdout"])
        manifest_file = outputs.get("manifest_file")
        
        if manifest_file and Path(manifest_file).exists():
            print(f"✅ Manifest skapad: {manifest_file}")
            return Path(manifest_file)
        else:
            # Fallback - försök hitta manifest fil
            expected_file = output_dir / f"deployment-manifest-{version}.json"
            if expected_file.exists():
                print(f"✅ Manifest hittad via fallback: {expected_file}")
                return expected_file
            else:
                raise RuntimeError("Kunde inte hitta skapad manifest-fil")
    
    def create_backup(self, version: str, output_dir: Path, manifest_file: Path) -> Path:
        """Skapa backup fil"""
        
        print("📦 Skapar backup fil...")
        
        backup_args = [
            "--version", version,
            "--output-dir", str(output_dir),
            "--manifest-file", str(manifest_file)
        ]
        
        result = self.run_script("create_backup.py", backup_args)
        
        # Parsa output för backup fil path
        outputs = self.parse_script_output(result["stdout"])
        backup_file = outputs.get("backup_file")
        backup_size = outputs.get("backup_size", "unknown")
        
        if backup_file and Path(backup_file).exists():
            print(f"✅ Backup skapad: {backup_file} ({self.format_size(backup_size)})")
            return Path(backup_file)
        else:
            # Fallback - leta efter backup fil i output directory
            backup_files = list(output_dir.glob(f"gridenforcer-{version}-*.tar.gz"))
            if backup_files:
                backup_file = max(backup_files, key=lambda p: p.stat().st_mtime)
                print(f"✅ Backup hittad via fallback: {backup_file}")
                return backup_file
            else:
                raise RuntimeError("Kunde inte hitta skapad backup-fil")
    
    def format_size(self, size_str: str) -> str:
        """Formatera filstorlek för display"""
        try:
            size_bytes = int(size_str)
            size_mb = size_bytes / 1024 / 1024
            return f"{size_mb:.1f} MB"
        except (ValueError, TypeError):
            return str(size_str)
    
    def create_deployment_summary(self, version: str, manifest_file: Path, backup_file: Path, output_dir: Path) -> Path:
        """Skapa sammanfattning av deployment artefakter"""
        
        # Läs manifest för metadata
        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        deployment_type = manifest.get("gridenforcer", {}).get("deployment_type", "unknown")
        previous_version = manifest.get("gridenforcer", {}).get("previous_version", "none")
        
        # Samla fil-information
        backup_size_mb = backup_file.stat().st_size / 1024 / 1024
        
        # Säker path-hantering - använd absoluta paths om relative misslyckas
        def safe_relative_path(file_path: Path) -> str:
            try:
                return str(file_path.relative_to(self.project_root))
            except ValueError:
                # Fallback till absolut path om relative_to misslyckas
                return str(file_path.absolute())
        
        summary = {
            "deployment_info": {
                "version": version,
                "deployment_type": deployment_type,
                "previous_version": previous_version,
                "created_at": datetime.now().isoformat()
            },
            "artifacts": {
                "manifest_file": {
                    "path": safe_relative_path(manifest_file),
                    "absolute_path": str(manifest_file.absolute()),
                    "size_bytes": manifest_file.stat().st_size
                },
                "backup_file": {
                    "path": safe_relative_path(backup_file),
                    "absolute_path": str(backup_file.absolute()),
                    "size_bytes": backup_file.stat().st_size,
                    "size_mb": round(backup_size_mb, 1)
                }
            },
            "deployment_instructions": {
                "manual_deployment": [
                    f"1. Överför {backup_file.name} till Home Assistant enhet",
                    "2. Gå till Settings > System > Backups",
                    "3. Klicka 'Restore' och välj backup-filen", 
                    "4. Starta om Home Assistant efter restore",
                    "5. Konfigurera GridEnforcer via Settings > Integrations",
                    "6. Kör python_scripts.gridenforcer_verify för att verifiera"
                ],
                "automated_deployment": [
                    "SSH deployment kommer i framtida version",
                    "För nu: använd manuell deployment via HA UI"
                ]
            },
            "git_info": manifest.get("git_info", {}),
            "build_info": manifest.get("build_info", {}),
            "debug_info": {
                "project_root": str(self.project_root.absolute()),
                "manifest_file_absolute": str(manifest_file.absolute()),
                "backup_file_absolute": str(backup_file.absolute()),
                "output_dir_absolute": str(output_dir.absolute())
            }
        }
        
        summary_file = output_dir / f"deployment-summary-{version}.json"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Deployment summary skapad: {summary_file}")
        return summary_file
    
    def create_all_artifacts(self, version: str, output_dir: Path, build_info: Optional[Dict] = None) -> Dict[str, Path]:
        """Huvudfunktion - skapa alla deployment artefakter"""
        
        print(f"🚀 Skapar deployment artefakter för GridEnforcer {version}")
        print("=" * 60)
        
        if not build_info:
            build_info = {
                "build_system": "local",
                "build_time": datetime.now().isoformat()
            }
        
        try:
            # 1. Skapa manifest
            manifest_file = self.create_manifest(version, output_dir, build_info)
            
            # 2. Skapa backup
            backup_file = self.create_backup(version, output_dir, manifest_file)
            
            # 3. Skapa deployment summary
            summary_file = self.create_deployment_summary(version, manifest_file, backup_file, output_dir)
            
            artifacts = {
                "manifest": manifest_file,
                "backup": backup_file, 
                "summary": summary_file
            }
            
            print("=" * 60)
            print("🎉 Alla deployment artefakter skapade framgångsrikt!")
            print(f"📁 Output directory: {output_dir}")
            
            for artifact_type, file_path in artifacts.items():
                size_mb = file_path.stat().st_size / 1024 / 1024
                print(f"   {artifact_type}: {file_path.name} ({size_mb:.1f} MB)")
            
            return artifacts
            
        except Exception as e:
            print("=" * 60)
            print(f"❌ Misslyckades att skapa deployment artefakter: {e}")
            raise


def main():
    # 🚨 DEBUG: Uncomment för lokal debugging
    # import sys
    sys.argv = ['script', '--version', 'v0.1.0', '--output-dir', 'deployment']
    
    parser = argparse.ArgumentParser(
        description="Skapa alla GridEnforcer deployment artefakter"
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
        help="Output directory för artefakter (default: deployment/)"
    )
    parser.add_argument(
        "--build-number",
        help="CI build number (valfritt)"
    )
    parser.add_argument(
        "--ci-system", 
        help="CI system namn (t.ex. github_actions)"
    )
    parser.add_argument(
        "--git-commit",
        help="Git commit hash"
    )
    
    args = parser.parse_args()
    
    # Build info från CI environment eller lokalt
    build_info = {
        "build_system": args.ci_system or "local",
        "build_number": args.build_number,
        "git_commit": args.git_commit,
        "build_time": datetime.now().isoformat()
    }
    
    creator = DeploymentArtifactsCreator()
    
    try:
        artifacts = creator.create_all_artifacts(args.version, args.output_dir, build_info)
        
        # CI/CD output
        if args.ci_system:
            print(f"::set-output name=manifest_file::{artifacts['manifest']}")
            print(f"::set-output name=backup_file::{artifacts['backup']}")
            print(f"::set-output name=summary_file::{artifacts['summary']}")
            print(f"::set-output name=version::{args.version}")
        
        print("\n🔗 Nästa steg:")
        print("1. Testa backup på din test-VM")
        print("2. Integrera i GitHub Actions pipeline") 
        print("3. Dokumentera deployment-processen")
        
    except Exception as e:
        print(f"❌ Kritiskt fel: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()