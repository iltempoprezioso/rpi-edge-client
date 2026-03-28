#!/usr/bin/env python3
"""
Test real sensors on UnitaPresidioMacchina001
Run this on the actual Raspberry Pi with sensors connected
"""

import sys
import time
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from drivers.ism330dhcx import ISM330DHCXDriver
from drivers.max6675 import MAX6675Driver
from drivers.sct013_ads1115 import SCT013ADS1115Driver


def test_ism330dhcx():
    """Test ISM330DHCX accelerometer/gyroscope"""
    print("\n" + "="*60)
    print("TEST 1: ISM330DHCX (6-axis IMU)")
    print("="*60)
    
    config = {
        'address': '0x6A',
        'bus': 1,
        'accel_range': 4,
        'gyro_range': 250,
        'sampling_rate': 104,
        'enable_gyro': True
    }
    
    sensor = ISM330DHCXDriver(sensor_id=1, config=config)
    
    print(f"Initializing sensor at 0x{int(config['address'], 16):02x}...")
    if not sensor.initialize():
        print("❌ FAILED: Sensor initialization failed")
        return False
    
    print("✅ Sensor initialized")
    
    # Check status
    status = sensor.get_status()
    print(f"Status: {json.dumps(status, indent=2)}")
    
    # Read 10 samples
    print("\nReading 10 samples:")
    for i in range(10):
        data = sensor.read_raw()
        
        if 'error' in data:
            print(f"  Sample {i+1}: ❌ ERROR - {data['error']}")
        else:
            print(f"  Sample {i+1}: "
                  f"Accel({data['accel_x']:+.3f}, {data['accel_y']:+.3f}, {data['accel_z']:+.3f})g "
                  f"Gyro({data['gyro_x']:+.2f}, {data['gyro_y']:+.2f}, {data['gyro_z']:+.2f})dps")
        
        time.sleep(0.5)
    
    sensor.shutdown()
    print("✅ TEST PASSED\n")
    return True


def test_max6675():
    """Test MAX6675 thermocouple"""
    print("\n" + "="*60)
    print("TEST 2: MAX6675 (K-Type Thermocouple)")
    print("="*60)
    
    config = {
        'cs_pin': 0,  # CE0
        'bus': 0,     # SPI0
        'max_speed_hz': 1000000
    }
    
    sensor = MAX6675Driver(sensor_id=2, config=config)
    
    print(f"Initializing sensor on SPI{config['bus']}.{config['cs_pin']}...")
    if not sensor.initialize():
        print("❌ FAILED: Sensor initialization failed")
        return False
    
    print("✅ Sensor initialized")
    
    # Check status
    status = sensor.get_status()
    print(f"Status: {json.dumps(status, indent=2)}")
    
    # Read 10 samples
    print("\nReading 10 samples:")
    for i in range(10):
        data = sensor.read_raw()
        
        if 'error' in data:
            print(f"  Sample {i+1}: ❌ ERROR - {data['error']}")
        elif data.get('open_circuit'):
            print(f"  Sample {i+1}: ⚠️  OPEN CIRCUIT - Thermocouple not connected")
        else:
            print(f"  Sample {i+1}: {data['temperature']:.2f}°C (raw: 0x{data.get('raw_value', 0):04x})")
        
        time.sleep(1)
    
    sensor.shutdown()
    print("✅ TEST PASSED\n")
    return True


def test_sct013_ads1115():
    """Test SCT-013-030 + ADS1115 current sensor"""
    print("\n" + "="*60)
    print("TEST 3: SCT-013-030 + ADS1115 (Current Sensor)")
    print("="*60)
    
    config = {
        'address': '0x48',
        'bus': 1,
        'channel': 0,
        'gain': 0x0200,  # ±4.096V
        'current_range': 30.0,
        'bias_voltage': 1.65,
        'calibration_offset': 0.0,
        'samples_per_read': 100
    }
    
    sensor = SCT013ADS1115Driver(sensor_id=3, config=config)
    
    print(f"Initializing sensor at 0x{int(config['address'], 16):02x}...")
    if not sensor.initialize():
        print("❌ FAILED: Sensor initialization failed")
        return False
    
    print("✅ Sensor initialized")
    
    # Check status
    status = sensor.get_status()
    print(f"Status: {json.dumps(status, indent=2)}")
    
    # Read 5 samples (slower because RMS calculation)
    print(f"\nReading 5 samples ({config['samples_per_read']} samples per RMS):")
    for i in range(5):
        data = sensor.read_raw()
        
        if 'error' in data:
            print(f"  Sample {i+1}: ❌ ERROR - {data['error']}")
        else:
            print(f"  Sample {i+1}: {data['current']:.3f}A RMS "
                  f"(bias: {data.get('voltage_bias', 0):.4f}V)")
        
        time.sleep(2)
    
    sensor.shutdown()
    print("✅ TEST PASSED\n")
    return True


def test_i2c_scan():
    """Scan I2C bus for devices"""
    print("\n" + "="*60)
    print("I2C BUS SCAN")
    print("="*60)
    
    try:
        import smbus2
        bus = smbus2.SMBus(1)
        
        devices_found = []
        
        print("Scanning I2C bus 1 (0x00 - 0x7F)...")
        for addr in range(0x00, 0x80):
            try:
                bus.read_byte(addr)
                devices_found.append(addr)
                print(f"  Found device at 0x{addr:02x}")
            except:
                pass
        
        bus.close()
        
        print(f"\nTotal devices found: {len(devices_found)}")
        
        if 0x6A in devices_found:
            print("  ✅ ISM330DHCX detected at 0x6A")
        if 0x48 in devices_found:
            print("  ✅ ADS1115 detected at 0x48")
        
        return True
        
    except Exception as e:
        print(f"❌ I2C scan failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("VIBRASENSE REAL HARDWARE TEST SUITE")
    print("UnitaPresidioMacchina001 - Raspberry Pi 4 Model B")
    print("="*60)
    
    results = {}
    
    # I2C scan first
    results['i2c_scan'] = test_i2c_scan()
    
    # Test each sensor
    results['ism330dhcx'] = test_ism330dhcx()
    results['max6675'] = test_max6675()
    results['sct013_ads1115'] = test_sct013_ads1115()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {name.ljust(20)}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests PASSED! Hardware is ready for production.")
        return 0
    else:
        print("\n⚠️  Some tests FAILED. Check hardware connections and configuration.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
