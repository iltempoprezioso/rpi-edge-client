"""
MAX31855 Thermocouple Amplifier Driver (SPI interface).
Measures temperature using K-type thermocouples.
"""
from typing import Dict, Any, Optional
import logging
import time
from .base_driver import SensorDriver

# Mock mode for development without hardware
MOCK_MODE = True

try:
    import spidev
    MOCK_MODE = False
except ImportError:
    logging.warning("spidev not available, running in MOCK mode")


class MAX31855Driver(SensorDriver):
    """Driver for MAX31855 thermocouple amplifier."""
    
    def __init__(self, sensor_id: int, config: Dict[str, Any]):
        """
        Initialize MAX31855 driver.
        
        Args:
            sensor_id: Unique sensor identifier
            config: Configuration dict with keys:
                - cs_pin: Chip select GPIO pin (not used in software SPI)
                - spi_bus: SPI bus number (default 0)
                - spi_device: SPI device number (default 0)
                - thermocouple_type: Type of thermocouple (K, J, T, etc.)
        """
        super().__init__(sensor_id, config)
        
        self.cs_pin = config.get('cs_pin', 8)
        self.spi_bus = config.get('spi_bus', 0)
        self.spi_device = config.get('spi_device', 0)
        self.thermocouple_type = config.get('thermocouple_type', 'K')
        
        self.spi = None
        self.mock_temp_base = 50.0
        
    def initialize(self) -> bool:
        """Initialize MAX31855 sensor."""
        try:
            if MOCK_MODE:
                self.logger.info(f"MAX31855 (MOCK) initialized on sensor {self.sensor_id}")
                self.is_initialized = True
                return True
            
            # Initialize SPI
            self.spi = spidev.SpiDev()
            self.spi.open(self.spi_bus, self.spi_device)
            
            # SPI settings for MAX31855
            self.spi.max_speed_hz = 5000000  # 5 MHz
            self.spi.mode = 0  # CPOL=0, CPHA=0
            
            self.is_initialized = True
            self.logger.info(f"MAX31855 initialized on SPI {self.spi_bus}.{self.spi_device}, "
                           f"thermocouple type {self.thermocouple_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MAX31855: {e}")
            self.increment_error_count()
            return False
    
    def read_raw(self) -> Optional[Dict[str, Any]]:
        """
        Read temperature data.
        
        Returns:
            Dictionary with keys: timestamp, temperature, internal_temp, unit
        """
        try:
            if MOCK_MODE:
                return self._read_mock_data()
            
            if not self.is_initialized:
                self.logger.error("Sensor not initialized")
                return None
            
            # Read 4 bytes from MAX31855
            data = self.spi.readbytes(4)
            
            # Check for errors
            if data[3] & 0x01:
                self.logger.error("Thermocouple open circuit")
                self.increment_error_count()
                return None
            
            if data[3] & 0x02:
                self.logger.error("Thermocouple short to GND")
                self.increment_error_count()
                return None
            
            if data[3] & 0x04:
                self.logger.error("Thermocouple short to VCC")
                self.increment_error_count()
                return None
            
            # Extract thermocouple temperature (bits 31-18)
            temp_raw = ((data[0] << 8) | data[1]) >> 2
            
            # Convert to signed value
            if temp_raw & 0x2000:
                temp_raw -= 16384
            
            # Convert to Celsius (0.25°C per bit)
            temperature = temp_raw * 0.25
            
            # Extract internal temperature (bits 15-4)
            internal_raw = ((data[2] << 8) | data[3]) >> 4
            
            # Convert to signed value
            if internal_raw & 0x800:
                internal_raw -= 4096
            
            # Convert to Celsius (0.0625°C per bit)
            internal_temp = internal_raw * 0.0625
            
            result = {
                'timestamp': time.time(),
                'temperature': round(temperature, 2),
                'internal_temp': round(internal_temp, 2),
                'unit': 'celsius'
            }
            
            self.reset_error_count()
            return result
            
        except Exception as e:
            self.logger.error(f"Error reading MAX31855: {e}")
            self.increment_error_count()
            return None
    
    def close(self):
        """Close SPI connection."""
        if self.spi and not MOCK_MODE:
            self.spi.close()
        self.is_initialized = False
        self.logger.info("MAX31855 closed")
    
    def _read_mock_data(self) -> Dict[str, Any]:
        """Generate mock temperature data for testing."""
        import random
        
        # Simulate realistic temperature with gradual changes
        self.mock_temp_base += random.uniform(-0.5, 0.5)
        
        # Keep temperature in realistic range (40-80°C)
        self.mock_temp_base = max(40.0, min(80.0, self.mock_temp_base))
        
        # Add small noise
        temperature = self.mock_temp_base + random.uniform(-0.2, 0.2)
        internal_temp = 25.0 + random.uniform(-1.0, 1.0)
        
        return {
            'timestamp': time.time(),
            'temperature': round(temperature, 2),
            'internal_temp': round(internal_temp, 2),
            'unit': 'celsius'
        }
