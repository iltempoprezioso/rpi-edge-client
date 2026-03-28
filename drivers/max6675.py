#!/usr/bin/env python3
"""
MAX6675 K-Type Thermocouple Driver
SPI interface, 0.25°C resolution, range 0-1024°C
Datasheet: https://datasheets.maximintegrated.com/en/ds/MAX6675.pdf
"""

import time
import logging
from typing import Dict, Optional

try:
    import spidev
    SPIDEV_AVAILABLE = True
except ImportError:
    SPIDEV_AVAILABLE = False

from drivers.base_driver import SensorDriver
from drivers.retry_utils import spi_retry

logger = logging.getLogger(__name__)


class MAX6675Driver(SensorDriver):
    """
    Driver for MAX6675 K-type thermocouple amplifier
    
    Features:
    - Temperature range: 0°C to +1024°C
    - Resolution: 0.25°C (12-bit)
    - SPI interface (read-only, clock max 4.3 MHz)
    - Cold-junction compensation
    - Open thermocouple detection
    
    Tested configuration:
    - SPI0, CE0 (GPIO8)
    - Clock: 1 MHz
    - Mode: 0 (CPOL=0, CPHA=0)
    """
    
    # Constants
    TEMP_RESOLUTION = 0.25  # °C per bit
    MAX_TEMP = 1024.0       # Maximum temperature (°C)
    
    def __init__(self, sensor_id: int, config: Dict):
        """
        Initialize MAX6675 driver
        
        Args:
            sensor_id: Unique sensor identifier
            config: Configuration dictionary with:
                - cs_pin: SPI chip select (0 for CE0, 1 for CE1)
                - bus: SPI bus number (default 0)
                - max_speed_hz: SPI clock speed (default 1000000 = 1MHz)
        """
        super().__init__(sensor_id, config)
        
        self.cs_pin = config.get('cs_pin', 0)  # CE0 default
        self.bus_number = config.get('bus', 0)  # SPI0 default
        self.max_speed_hz = config.get('max_speed_hz', 1000000)  # 1 MHz default
        
        self.spi: Optional[spidev.SpiDev] = None
    
    def initialize(self) -> bool:
        """Initialize SPI connection"""
        try:
            if not SPIDEV_AVAILABLE:
                logger.warning(f"Sensor {self.sensor_id}: spidev not available, using mock mode")
                self.mock_mode = True
                return True
            
            # Open SPI device
            self.spi = spidev.SpiDev()
            self.spi.open(self.bus_number, self.cs_pin)
            
            # Configure SPI
            self.spi.max_speed_hz = self.max_speed_hz
            self.spi.mode = 0b00  # CPOL=0, CPHA=0
            
            logger.info(f"Sensor {self.sensor_id}: MAX6675 initialized on SPI{self.bus_number}.{self.cs_pin}, {self.max_speed_hz} Hz")
            
            # Test read
            test_data = self._read_raw_bytes()
            if test_data is None:
                logger.error(f"Sensor {self.sensor_id}: Test read failed")
                return False
            
            # Check if thermocouple is connected
            if test_data & 0x04:
                logger.warning(f"Sensor {self.sensor_id}: No thermocouple detected (open circuit)")
            else:
                temp = self._parse_temperature(test_data)
                logger.info(f"Sensor {self.sensor_id}: Initial temperature: {temp:.2f}°C")
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Sensor {self.sensor_id}: Initialization failed: {e}")
            return False
    
    @spi_retry(max_retries=3, delay=0.01)
    def _read_raw_bytes(self) -> Optional[int]:
        """
        Read 2 bytes from MAX6675
        
        Returns:
            16-bit value or None on error
        """
        try:
            # Read 2 bytes
            raw = self.spi.xfer2([0x00, 0x00])
            value = (raw[0] << 8) | raw[1]
            return value
            
        except Exception as e:
            logger.error(f"Sensor {self.sensor_id}: SPI read failed: {e}")
            return None
    
    def _parse_temperature(self, raw_value: int) -> float:
        """
        Parse raw 16-bit value to temperature
        
        Data format (MSB first):
        Bit 15: Always 0
        Bit 14-3: 12-bit temperature (°C / 0.25)
        Bit 2: Thermocouple input (1=open, 0=connected)
        Bit 1: Device ID (always 0)
        Bit 0: Three-state (always 0)
        
        Args:
            raw_value: 16-bit raw value from sensor
        
        Returns:
            Temperature in °C
        """
        # Extract temperature bits (14-3)
        temp_raw = (raw_value >> 3) & 0x0FFF
        
        # Convert to Celsius
        temperature = temp_raw * self.TEMP_RESOLUTION
        
        return temperature
    
    def read_raw(self) -> Dict:
        """
        Read temperature from MAX6675
        
        Returns:
            Dictionary with:
            - temperature: Temperature in °C
            - open_circuit: True if thermocouple is disconnected
            - timestamp: Unix timestamp
        """
        if self.mock_mode:
            return self._generate_mock_data()
        
        try:
            raw_value = self._read_raw_bytes()
            
            if raw_value is None:
                return {
                    'error': 'SPI read failed',
                    'timestamp': time.time()
                }
            
            # Check thermocouple connection (bit 2)
            open_circuit = bool(raw_value & 0x04)
            
            if open_circuit:
                logger.warning(f"Sensor {self.sensor_id}: Thermocouple not connected")
                return {
                    'temperature': None,
                    'open_circuit': True,
                    'error': 'Thermocouple disconnected',
                    'timestamp': time.time()
                }
            
            # Parse temperature
            temperature = self._parse_temperature(raw_value)
            
            # Sanity check
            if temperature < 0 or temperature > self.MAX_TEMP:
                logger.warning(f"Sensor {self.sensor_id}: Temperature out of range: {temperature}°C")
            
            return {
                'temperature': temperature,
                'open_circuit': False,
                'raw_value': raw_value,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Sensor {self.sensor_id}: Read failed: {e}")
            return {
                'error': str(e),
                'timestamp': time.time()
            }
    
    def _generate_mock_data(self) -> Dict:
        """Generate mock temperature data for testing"""
        import random
        
        # Simulate ambient temperature with small fluctuations
        base_temp = 25.0
        temperature = base_temp + random.uniform(-2, 2)
        
        return {
            'temperature': round(temperature / self.TEMP_RESOLUTION) * self.TEMP_RESOLUTION,
            'open_circuit': False,
            'timestamp': time.time()
        }
    
    def get_status(self) -> Dict:
        """Get sensor status"""
        if self.mock_mode:
            return {
                'initialized': True,
                'mock_mode': True,
                'healthy': True
            }
        
        try:
            # Read and check for errors
            data = self.read_raw()
            
            healthy = 'error' not in data and not data.get('open_circuit', False)
            
            return {
                'initialized': self.initialized,
                'mock_mode': False,
                'healthy': healthy,
                'open_circuit': data.get('open_circuit', False),
                'last_temperature': data.get('temperature')
            }
            
        except Exception as e:
            logger.error(f"Sensor {self.sensor_id}: Status check failed: {e}")
            return {
                'initialized': self.initialized,
                'healthy': False,
                'error': str(e)
            }
    
    def shutdown(self) -> bool:
        """Close SPI connection"""
        try:
            if not self.mock_mode and self.spi:
                self.spi.close()
                logger.info(f"Sensor {self.sensor_id}: SPI closed")
            
            self.initialized = False
            return True
            
        except Exception as e:
            logger.error(f"Sensor {self.sensor_id}: Shutdown failed: {e}")
            return False
