"""
Sensor Manager - Manages multiple sensors and data acquisition.
"""
import json
import logging
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

from drivers import ADXL345Driver, MAX31855Driver, ACS712Driver, SensorDriver


class SensorManager:
    """Manages all sensors and coordinates data acquisition."""
    
    # Map sensor driver names to classes
    DRIVER_MAP = {
        'adxl345': ADXL345Driver,
        'max31855': MAX31855Driver,
        'acs712': ACS712Driver
    }
    
    def __init__(self, config_path: str):
        """
        Initialize sensor manager.
        
        Args:
            config_path: Path to sensors configuration file
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path
        self.sensors: Dict[int, SensorDriver] = {}
        self.sensor_configs: List[Dict[str, Any]] = []
        self.is_running = False
        
        self._load_configuration()
    
    def _load_configuration(self):
        """Load sensor configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            self.machine_id = config.get('machine_id')
            self.machine_name = config.get('machine_name')
            self.company_id = config.get('company_id')
            self.sensor_configs = config.get('sensors', [])
            self.acquisition_config = config.get('acquisition', {})
            
            self.logger.info(f"Loaded configuration for machine '{self.machine_name}' "
                           f"(ID: {self.machine_id}) with {len(self.sensor_configs)} sensors")
            
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration file: {e}")
            raise
    
    def initialize_all_sensors(self) -> bool:
        """
        Initialize all enabled sensors.
        
        Returns:
            True if all sensors initialized successfully
        """
        success_count = 0
        
        for sensor_config in self.sensor_configs:
            if not sensor_config.get('enabled', True):
                self.logger.info(f"Sensor {sensor_config['sensor_id']} is disabled, skipping")
                continue
            
            sensor_id = sensor_config['sensor_id']
            driver_name = sensor_config['driver']
            
            # Get driver class
            driver_class = self.DRIVER_MAP.get(driver_name)
            if not driver_class:
                self.logger.error(f"Unknown driver: {driver_name}")
                continue
            
            try:
                # Create driver instance
                driver = driver_class(sensor_id, sensor_config['config'])
                
                # Initialize sensor
                if driver.initialize():
                    self.sensors[sensor_id] = driver
                    success_count += 1
                    self.logger.info(f"✓ Sensor {sensor_id} ({sensor_config['name']}) initialized")
                else:
                    self.logger.error(f"✗ Failed to initialize sensor {sensor_id}")
                
            except Exception as e:
                self.logger.error(f"Error initializing sensor {sensor_id}: {e}")
        
        total_enabled = sum(1 for s in self.sensor_configs if s.get('enabled', True))
        
        if success_count == total_enabled:
            self.logger.info(f"All {success_count} sensors initialized successfully")
            return True
        else:
            self.logger.warning(f"Only {success_count}/{total_enabled} sensors initialized")
            return False
    
    def read_all_sensors(self) -> Optional[Dict[str, Any]]:
        """
        Read data from all sensors.
        
        Returns:
            Dictionary with readings from all sensors
        """
        readings = []
        timestamp = time.time()
        
        for sensor_id, driver in self.sensors.items():
            try:
                # Get sensor config
                sensor_config = next(
                    (s for s in self.sensor_configs if s['sensor_id'] == sensor_id),
                    None
                )
                
                if not sensor_config:
                    continue
                
                # Read sensor data
                raw_data = driver.read_raw()
                
                if raw_data:
                    reading = {
                        'sensor_id': sensor_id,
                        'sensor_name': sensor_config['name'],
                        'type': sensor_config['type'],
                        'timestamp': raw_data.get('timestamp', timestamp),
                        'data': raw_data
                    }
                    readings.append(reading)
                else:
                    self.logger.warning(f"No data from sensor {sensor_id}")
                    
                    # Check if sensor is unhealthy
                    if not driver.is_healthy():
                        self.logger.error(f"Sensor {sensor_id} is unhealthy, attempting recovery")
                        self._recover_sensor(sensor_id, driver)
                
            except Exception as e:
                self.logger.error(f"Error reading sensor {sensor_id}: {e}")
        
        if not readings:
            self.logger.error("No sensor readings available")
            return None
        
        result = {
            'timestamp': timestamp,
            'machine_id': self.machine_id,
            'company_id': self.company_id,
            'readings': readings
        }
        
        return result
    
    def _recover_sensor(self, sensor_id: int, driver: SensorDriver):
        """
        Attempt to recover a failed sensor.
        
        Args:
            sensor_id: Sensor identifier
            driver: Sensor driver instance
        """
        try:
            self.logger.info(f"Attempting to recover sensor {sensor_id}")
            
            # Close existing connection
            driver.close()
            time.sleep(1)
            
            # Reinitialize
            if driver.initialize():
                driver.reset_error_count()
                self.logger.info(f"Sensor {sensor_id} recovered successfully")
            else:
                self.logger.error(f"Failed to recover sensor {sensor_id}")
                
        except Exception as e:
            self.logger.error(f"Error recovering sensor {sensor_id}: {e}")
    
    def get_sensor_status(self) -> Dict[str, Any]:
        """
        Get status of all sensors.
        
        Returns:
            Dictionary with sensor health status
        """
        sensors_status = []
        
        for sensor_id, driver in self.sensors.items():
            sensor_config = next(
                (s for s in self.sensor_configs if s['sensor_id'] == sensor_id),
                None
            )
            
            if sensor_config:
                status = {
                    'sensor_id': sensor_id,
                    'name': sensor_config['name'],
                    'type': sensor_config['type'],
                    'is_initialized': driver.is_initialized,
                    'is_healthy': driver.is_healthy(),
                    'error_count': driver.get_error_count()
                }
                sensors_status.append(status)
        
        return {
            'machine_id': self.machine_id,
            'total_sensors': len(self.sensors),
            'healthy_sensors': sum(1 for s in sensors_status if s['is_healthy']),
            'sensors': sensors_status
        }
    
    def close_all_sensors(self):
        """Close all sensor connections."""
        for sensor_id, driver in self.sensors.items():
            try:
                driver.close()
                self.logger.info(f"Sensor {sensor_id} closed")
            except Exception as e:
                self.logger.error(f"Error closing sensor {sensor_id}: {e}")
        
        self.sensors.clear()
        self.logger.info("All sensors closed")
    
    def get_read_interval(self) -> int:
        """Get configured read interval in seconds."""
        return self.acquisition_config.get('read_interval', 30)
    
    def is_acquisition_enabled(self) -> bool:
        """Check if data acquisition is enabled."""
        return self.acquisition_config.get('enabled', True)
