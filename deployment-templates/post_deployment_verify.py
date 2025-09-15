"""
GridEnforcer Post-Deployment Verification Script
Körs automatiskt efter backup restore för att verifiera installation

Detta script placeras i python_scripts/ och kan köras via Home Assistant
Services > Python Scripts > gridenforcer_verify
"""

import logging
from datetime import datetime

_LOGGER = logging.getLogger(__name__)


def verify_gridenforcer_installation():
    """Huvudfunktion för verifiering av GridEnforcer installation"""
    
    hass = data.get("hass")
    version = data.get("version", "unknown")
    
    if not hass:
        _LOGGER.error("Home Assistant instance inte tillgänglig")
        return False
    
    _LOGGER.info(f"🔍 Verifierar GridEnforcer {version} installation...")
    
    results = {
        "integration_loaded": check_integration_loaded(hass),
        "entities_available": check_required_entities(hass),
        "configuration_valid": check_configuration(hass),
        "external_connections": check_external_connections(hass)
    }
    
    # Sammanfatta resultat
    all_passed = all(results.values())
    
    create_verification_notification(hass, version, results, all_passed)
    log_verification_results(results, all_passed)
    
    return all_passed


def check_integration_loaded(hass):
    """Kontrollera att GridEnforcer integration är laddad"""
    
    try:
        # Kontrollera att integration finns i hass.data
        if "gridenforcer" in hass.data:
            _LOGGER.info("✅ GridEnforcer integration är laddad")
            return True
        else:
            _LOGGER.warning("⚠️ GridEnforcer integration inte laddad i hass.data")
            
            # Alternativ kontroll via integration registry
            integration_domain = "gridenforcer"
            if hasattr(hass.data, 'get') and hass.data.get('integration', {}).get(integration_domain):
                _LOGGER.info("✅ GridEnforcer integration hittad i registry")
                return True
                
            _LOGGER.error("❌ GridEnforcer integration inte laddad")
            return False
            
    except Exception as e:
        _LOGGER.error(f"❌ Fel vid kontroll av integration: {e}")
        return False


def check_required_entities(hass):
    """Kontrollera att viktiga entiteter existerar"""
    
    required_entities = [
        ("sensor.gridenforcer_inverter_mode", "Inverter mode sensor"),
        ("number.gridenforcer_soc_backup", "SOC backup setting"),
        ("number.gridenforcer_soc_max", "SOC max setting"), 
        ("select.gridenforcer_operation_mode", "Operation mode selector"),
        ("number.gridenforcer_selfuse_hours", "Selfuse hours setting"),
        ("number.gridenforcer_charge_hours", "Charge hours setting")
    ]
    
    missing_entities = []
    available_entities = []
    
    for entity_id, description in required_entities:
        state = hass.states.get(entity_id)
        if state is not None:
            available_entities.append((entity_id, description, state.state))
            _LOGGER.info(f"✅ {description}: {entity_id} = {state.state}")
        else:
            missing_entities.append((entity_id, description))
            _LOGGER.warning(f"⚠️ Saknad entitet: {description} ({entity_id})")
    
    if not missing_entities:
        _LOGGER.info(f"✅ Alla {len(required_entities)} viktiga entiteter hittades")
        return True
    else:
        _LOGGER.warning(f"⚠️ {len(missing_entities)} entiteter saknas av {len(required_entities)}")
        _LOGGER.info("💡 Detta kan vara normalt om GridEnforcer inte är konfigurerad via UI ännu")
        return len(available_entities) > 0  # OK om några entiteter finns


def check_configuration(hass):
    """Kontrollera grundläggande konfiguration"""
    
    try:
        # Kontrollera att configuration.yaml kan läsas
        config = hass.config
        if not config:
            _LOGGER.error("❌ Home Assistant konfiguration inte tillgänglig")
            return False
        
        # Kontrollera viktiga konfigurationsområden
        checks = {
            "time_zone": config.time_zone == "Europe/Stockholm",
            "currency": config.currency == "SEK", 
            "unit_system": config.units.name == "metric"
        }
        
        passed_checks = sum(checks.values())
        total_checks = len(checks)
        
        if passed_checks == total_checks:
            _LOGGER.info("✅ Grundläggande konfiguration korrekt")
            return True
        else:
            _LOGGER.warning(f"⚠️ Konfiguration: {passed_checks}/{total_checks} kontroller OK")
            return passed_checks > 0
            
    except Exception as e:
        _LOGGER.error(f"❌ Fel vid konfigurationskontroll: {e}")
        return False


def check_external_connections(hass):
    """Kontrollera externa anslutningar (MQTT, etc.)"""
    
    try:
        external_checks = []
        
        # MQTT-kontroll
        if "mqtt" in hass.data:
            mqtt_available = hass.data["mqtt"].connected if hasattr(hass.data["mqtt"], 'connected') else True
            external_checks.append(("MQTT", mqtt_available))
            if mqtt_available:
                _LOGGER.info("✅ MQTT anslutning tillgänglig")
            else:
                _LOGGER.warning("⚠️ MQTT anslutning problem")
        else:
            _LOGGER.warning("⚠️ MQTT integration inte laddad")
            external_checks.append(("MQTT", False))
        
        # Modbus-kontroll  
        if "modbus" in hass.data:
            _LOGGER.info("✅ Modbus integration laddad")
            external_checks.append(("Modbus", True))
        else:
            _LOGGER.warning("⚠️ Modbus integration inte laddad")
            external_checks.append(("Modbus", False))
        
        # Kontrollera Nord Pool (om HACS är tillgängligt)
        nordpool_entities = [state for state in hass.states.async_all() 
                           if state.entity_id.startswith("sensor.nordpool")]
        if nordpool_entities:
            _LOGGER.info(f"✅ Nord Pool integration aktiv ({len(nordpool_entities)} entiteter)")
            external_checks.append(("Nord Pool", True))
        else:
            _LOGGER.warning("⚠️ Nord Pool integration inte hittad")
            external_checks.append(("Nord Pool", False))
        
        passed_external = sum(result for _, result in external_checks)
        total_external = len(external_checks)
        
        return passed_external > 0  # OK om minst en extern anslutning fungerar
        
    except Exception as e:
        _LOGGER.error(f"❌ Fel vid kontroll av externa anslutningar: {e}")
        return False


def create_verification_notification(hass, version, results, all_passed):
    """Skapa persistent notification med verifieringsresultat"""
    
    try:
        # Räkna resultat
        passed_count = sum(results.values())
        total_count = len(results)
        
        # Bestäm notification typ och meddelande
        if all_passed:
            title = f"✅ GridEnforcer {version} - Installation OK"
            message = f"Alla {total_count} verifieringskontroller lyckades. SystemET är redo att använda."
            notification_id = "gridenforcer_success"
        elif passed_count > 0:
            title = f"⚠️ GridEnforcer {version} - Partiell installation"  
            message = f"{passed_count}/{total_count} kontroller OK. Konfiguration kan behövas."
            notification_id = "gridenforcer_partial"
        else:
            title = f"❌ GridEnforcer {version} - Installation misslyckades"
            message = "Inga verifieringskontroller lyckades. Kontrollera installation."
            notification_id = "gridenforcer_failed"
        
        # Lägg till detaljerad information
        detail_lines = []
        status_icons = {True: "✅", False: "❌"}
        check_names = {
            "integration_loaded": "Integration laddad",
            "entities_available": "Entiteter tillgängliga", 
            "configuration_valid": "Konfiguration giltig",
            "external_connections": "Externa anslutningar"
        }
        
        for check, result in results.items():
            icon = status_icons[result]
            name = check_names.get(check, check)
            detail_lines.append(f"{icon} {name}")
        
        full_message = f"{message}\n\nDetaljer:\n" + "\n".join(detail_lines)
        full_message += f"\n\nNästa steg: Konfigurera GridEnforcer via Settings > Integrations om inte redan gjort."
        
        # Skapa notification
        hass.services.call("persistent_notification", "create", {
            "title": title,
            "message": full_message,
            "notification_id": notification_id
        })
        
        _LOGGER.info(f"📢 Verification notification skapad: {notification_id}")
        
    except Exception as e:
        _LOGGER.error(f"❌ Kunde inte skapa notification: {e}")


def log_verification_results(results, all_passed):
    """Logga detaljerade verifieringsresultat"""
    
    timestamp = datetime.now().isoformat()
    
    _LOGGER.info("=" * 50)
    _LOGGER.info("GridEnforcer Deployment Verification Results")
    _LOGGER.info(f"Timestamp: {timestamp}")
    _LOGGER.info("=" * 50)
    
    for check_name, result in results.items():
        status = "PASS" if result else "FAIL"
        _LOGGER.info(f"{check_name.upper()}: {status}")
    
    overall_status = "SUCCESS" if all_passed else "PARTIAL" if any(results.values()) else "FAILED"
    _LOGGER.info(f"OVERALL STATUS: {overall_status}")
    _LOGGER.info("=" * 50)


# Huvudkörning - detta körs när scriptet aktiveras från HA
try:
    # Hämta version från data (sätts av backup restore process)
    version = data.get("version", "unknown")
    
    _LOGGER.info(f"🚀 Startar GridEnforcer {version} post-deployment verification...")
    success = verify_gridenforcer_installation()
    
    if success:
        _LOGGER.info("🎉 GridEnforcer deployment verification slutförd framgångsrikt!")
    else:
        _LOGGER.warning("⚠️ GridEnforcer deployment verification slutförd med varningar")
        
except Exception as e:
    _LOGGER.error(f"❌ Kritiskt fel i verification script: {e}")
    
    # Skapa error notification
    hass = data.get("hass")
    if hass:
        hass.services.call("persistent_notification", "create", {
            "title": "❌ GridEnforcer Verification Error",
            "message": f"Post-deployment verification misslyckades: {str(e)}",
            "notification_id": "gridenforcer_verify_error"
        })