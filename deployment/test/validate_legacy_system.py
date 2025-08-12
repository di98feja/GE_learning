# tests/validate_legacy_system.py
"""
Validate that the legacy YAML system creates all expected entities
"""
import requests
import time
import sys

def validate_legacy_system():
    """Validate legacy system health"""
    base_url = "http://localhost:8123"
    
    # Wait for HA to be ready
    print("Waiting for Home Assistant to start...")
    for i in range(30):
        try:
            response = requests.get(f"{base_url}/api/", timeout=5)
            if response.status_code == 200:
                print("✓ Home Assistant is responding")
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
    else:
        print("❌ Home Assistant did not start")
        return False
    
    # Check for expected entities from legacy packages
    expected_entities = [
        'sensor.flower_fcr_up_available_watts',
        'sensor.flower_fcr_down_available_watts', 
        'binary_sensor.charge_battery_grid',
        'binary_sensor.discharge_battery',
        'input_number.hours_to_charge',
        'input_number.hours_to_sell'
    ]
    
    print("\nValidating legacy entities...")
    all_good = True
    
    for entity in expected_entities:
        try:
            response = requests.get(f"{base_url}/api/states/{entity}")
            if response.status_code == 200:
                print(f"✓ {entity}")
            else:
                print(f"❌ {entity} - Status: {response.status_code}")
                all_good = False
        except Exception as e:
            print(f"❌ {entity} - Error: {e}")
            all_good = False
    
    print(f"\nLegacy system validation: {'✓ PASSED' if all_good else '❌ FAILED'}")
    return all_good

if __name__ == "__main__":
    success = validate_legacy_system()
    sys.exit(0 if success else 1)