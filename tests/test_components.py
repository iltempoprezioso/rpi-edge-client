#!/usr/bin/env python3
"""
Test script for VibraSense Edge Client
Tests all components without requiring real hardware.
"""
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sensor_manager import SensorManager
from src.mqtt_client import MQTTClient
from src.buffer_manager import BufferManager
from src.data_processor import DataProcessor


def test_sensor_manager():
    """Test sensor manager."""
    print("\n" + "="*60)
    print("Testing Sensor Manager...")
    print("="*60)
    
    try:
        config_path = Path(__file__).parent.parent / 'config' / 'sensors.example.json'
        manager = SensorManager(str(config_path))
        
        print(f"✓ Configuration loaded: {manager.machine_name}")
        print(f"  - Machine ID: {manager.machine_id}")
        print(f"  - Sensors: {len(manager.sensor_configs)}")
        
        # Initialize sensors (mock mode)
        if manager.initialize_all_sensors():
            print("✓ All sensors initialized (MOCK mode)")
        else:
            print("✗ Sensor initialization failed")
            return False
        
        # Read sensor data
        readings = manager.read_all_sensors()
        if readings:
            print(f"✓ Sensor readings obtained: {len(readings['readings'])} sensors")
            for reading in readings['readings']:
                print(f"  - {reading['sensor_name']}: {reading['type']}")
        else:
            print("✗ No readings obtained")
            return False
        
        # Get status
        status = manager.get_sensor_status()
        print(f"✓ Sensor status: {status['healthy_sensors']}/{status['total_sensors']} healthy")
        
        manager.close_all_sensors()
        print("✓ Sensors closed")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_buffer_manager():
    """Test buffer manager."""
    print("\n" + "="*60)
    print("Testing Buffer Manager...")
    print("="*60)
    
    try:
        db_path = '/tmp/test_buffer.db'
        buffer = BufferManager(db_path, max_records=1000, cleanup_days=7)
        
        print("✓ Buffer manager initialized")
        
        # Create test reading
        test_reading = {
            'timestamp': 1234567890.0,
            'machine_id': 1,
            'company_id': 1,
            'readings': [
                {
                    'sensor_id': 1,
                    'sensor_name': 'Test Sensor',
                    'type': 'vibration',
                    'data': {'x': 1.5, 'y': 2.0, 'z': 1.8, 'unit': 'g'}
                }
            ]
        }
        
        # Save reading
        if buffer.save_reading(test_reading):
            print("✓ Test reading saved")
        else:
            print("✗ Failed to save reading")
            return False
        
        # Get untransmitted
        untransmitted = buffer.get_untransmitted_readings(limit=10)
        print(f"✓ Untransmitted readings: {len(untransmitted)}")
        
        # Mark as transmitted
        if untransmitted:
            ids = [r['id'] for r in untransmitted]
            buffer.mark_transmitted(ids)
            print(f"✓ Marked {len(ids)} readings as transmitted")
        
        # Get stats
        stats = buffer.get_buffer_stats()
        print(f"✓ Buffer stats: {stats['total_records']} total, {stats['transmitted']} transmitted")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mqtt_client():
    """Test MQTT client."""
    print("\n" + "="*60)
    print("Testing MQTT Client...")
    print("="*60)
    
    try:
        config_path = Path(__file__).parent.parent / 'config' / 'mqtt.example.json'
        client = MQTTClient(str(config_path), machine_id=1, company_id=1)
        
        print("✓ MQTT client initialized")
        print(f"  - Broker: {client.host}:{client.port}")
        print(f"  - TLS: {client.use_tls}")
        
        # Don't actually connect in test mode
        print("✓ MQTT client configuration valid")
        
        # Test topic formatting
        test_topic = client._format_topic(client.topic_readings)
        print(f"✓ Topic format: {test_topic}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_processor():
    """Test data processor."""
    print("\n" + "="*60)
    print("Testing Data Processor...")
    print("="*60)
    
    try:
        processor = DataProcessor(sampling_rate=1600)
        
        print("✓ Data processor initialized")
        
        # Test RMS calculation
        test_data = [1.0, 2.0, 3.0, 2.0, 1.0]
        rms = processor._calculate_rms(test_data)
        print(f"✓ RMS calculation: {rms:.3f}")
        
        # Test peak-to-peak
        p2p = processor._calculate_peak_to_peak(test_data)
        print(f"✓ Peak-to-peak calculation: {p2p:.3f}")
        
        # Test threshold check
        status = processor.check_threshold(5.0, {'warning': 4.5, 'critical': 7.1})
        print(f"✓ Threshold check: {status}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("VibraSense Edge Client - Component Tests")
    print("="*60)
    
    results = {}
    
    # Run tests
    results['Sensor Manager'] = test_sensor_manager()
    results['Buffer Manager'] = test_buffer_manager()
    results['MQTT Client'] = test_mqtt_client()
    results['Data Processor'] = test_data_processor()
    
    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for component, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{component}: {status}")
    
    print("="*60)
    
    # Exit code
    all_passed = all(results.values())
    if all_passed:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
