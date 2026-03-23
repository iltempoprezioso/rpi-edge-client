"""
ADXL345 Accelerometer Driver (I2C interface).
Measures vibrations on X, Y, Z axes.
"""
from typing import Dict, Any, Optional, List
import logging
import time
from .base_driver import SensorDriver

# Mock mode for development without hardware
MOCK_MODE = True

try:
    import smbus2
    MOCK_MODE = False
except ImportError:
    logging.warning("smbus2 not available, running in MOCK mode")


class ADXL345Driver(SensorDriver):
    """Driver for ADXL345 3-axis accelerometer."""
    
    # ADXL345 Registers
    POWER_CTL = 0x2D
    DATA_FORMAT = 0x31
    DATAX0 = 0x32
    BW_RATE = 0x2C
    
    # Configuration values
    MEASURE_MODE = 0x08
    SCALE_MULTIPLIER = 0.004  # g per LSB at +/-16g range
    
    def __init__(self, sensor_id: int, config: Dict[str, Any]):
        """
        Initialize ADXL345 driver.
        
        Args:
            sensor_id: Unique sensor identifier
            config: Configuration dict with keys:
                - address: I2C address (default 0x53)
                - bus: I2C bus number (default 1)
                - range: Measurement range in g (2, 4, 8, 16)
                - sampling_rate: Sampling rate in Hz
                - axes: List of axes to read ['x', 'y', 'z']
        """
        super().__init__(sensor_id, config)
        
        self.address = int(config.get('address', '0x53'), 16)
        self.bus_number = config.get('bus', 1)
        self.range_g = config.get('range', 16)
        self.sampling_rate = config.get('sampling_rate', 1600)
        self.axes = config.get('axes', ['x', 'y', 'z'])
        
        self.bus = None
        self.mock_data_counter = 0
        
    def initialize(self) -> bool:
        """Initialize ADXL345 sensor."""
        try:
            if MOCK_MODE:
                self.logger.info(f"ADXL345 (MOCK) initialized on sensor {self.sensor_id}")
                self.is_initialized = True
                return True
            
            # Initialize I2C bus
            self.bus = smbus2.SMBus(self.bus_number)
            
            # Set measurement mode
            self.bus.write_byte_data(self.address, self.POWER_CTL, self.MEASURE_MODE)
            
            # Set range
            range_value = self._get_range_value(self.range_g)
            self.bus.write_byte_data(self.address, self.DATA_FORMAT, range_value)
            
            # Set sampling rate
            rate_value = self._get_rate_value(self.sampling_rate)
            self.bus.write_byte_data(self.address, self.BW_RATE, rate_value)
            
            self.is_initialized = True
            self.logger.info(f"ADXL345 initialized on bus {self.bus_number}, "
                           f"address 0x{self.address:02x}, range ±{self.range_g}g, "
                           f"rate {self.sampling_rate}Hz")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ADXL345: {e}")
            self.increment_error_count()
            return False
    
    def read_raw(self) -> Optional[Dict[str, Any]]:
        """
        Read raw acceleration data.
        
        Returns:
            Dictionary with keys: timestamp, x, y, z (in g units)
        """
        try:
            if MOCK_MODE:
                return self._read_mock_data()
            
            if not self.is_initialized:
                self.logger.error("Sensor not initialized")
                return None
            
            # Read 6 bytes starting from DATAX0
            data = self.bus.read_i2c_block_data(self.address, self.DATAX0, 6)
            
            # Convert to signed 16-bit values
            x = self._bytes_to_int(data[0], data[1])
            y = self._bytes_to_int(data[2], data[3])
            z = self._bytes_to_int(data[4], data[5])
            
            # Convert to g units
            x_g = x * self.SCALE_MULTIPLIER
            y_g = y * self.SCALE_MULTIPLIER
            z_g = z * self.SCALE_MULTIPLIER
            
            result = {
                'timestamp': time.time(),
                'x': x_g,
                'y': y_g,
                'z': z_g,
                'unit': 'g'
            }
            
            self.reset_error_count()
            return result
            
        except Exception as e:
            self.logger.error(f"Error reading ADXL345: {e}")
            self.increment_error_count()
            return None
    
    def read_samples(self, num_samples: int) -> Optional[List[Dict[str, Any]]]:
        """
        Read multiple samples for signal processing.
        
        Args:
            num_samples: Number of samples to read
            
        Returns:
            List of sample dictionaries
        """
        samples = []
        
        for _ in range(num_samples):
            sample = self.read_raw()
            if sample:
                samples.append(sample)
            time.sleep(1.0 / self.sampling_rate)
        
        return samples if len(samples) == num_samples else None
    
    def close(self):
        """Close I2C bus connection."""
        if self.bus and not MOCK_MODE:
            self.bus.close()
        self.is_initialized = False
        self.logger.info("ADXL345 closed")
    
    def _bytes_to_int(self, low_byte: int, high_byte: int) -> int:
        """Convert two bytes to signed 16-bit integer."""
        value = (high_byte << 8) | low_byte
        if value >= 32768:
            value -= 65536
        return value
    
    def _get_range_value(self, range_g: int) -> int:
        """Get DATA_FORMAT register value for range."""
        range_map = {2: 0x00, 4: 0x01, 8: 0x02, 16: 0x03}
        return range_map.get(range_g, 0x03)  # Default to ±16g
    
    def _get_rate_value(self, rate_hz: int) -> int:
        """Get BW_RATE register value for sampling rate."""
        rate_map = {
            100: 0x0A,
            200: 0x0B,
            400: 0x0C,
            800: 0x0D,
            1600: 0x0E,
            3200: 0x0F
        }
        return rate_map.get(rate_hz, 0x0E)  # Default to 1600Hz
    
    def _read_mock_data(self) -> Dict[str, Any]:
        """Generate mock vibration data for testing."""
        import math
        
        # Simulate realistic vibration patterns
        self.mock_data_counter += 1
        t = self.mock_data_counter * 0.01
        
        # Base vibration + some noise
        x = 0.5 * math.sin(2 * math.pi * 10 * t) + 0.1 * math.sin(2 * math.pi * 50 * t)
        y = 0.3 * math.sin(2 * math.pi * 15 * t) + 0.1 * math.cos(2 * math.pi * 40 * t)
        z = 0.2 * math.sin(2 * math.pi * 5 * t) + 0.05 * math.sin(2 * math.pi * 60 * t)
        
        return {
            'timestamp': time.time(),
            'x': x,
            'y': y,
            'z': z,
            'unit': 'g'
        }
