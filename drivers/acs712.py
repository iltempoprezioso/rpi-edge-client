"""
ACS712 Current Sensor Driver (via MCP3008 ADC, SPI interface).
Measures AC/DC current using Hall effect sensor.
"""
from typing import Dict, Any, Optional
import logging
import time
import math
from .base_driver import SensorDriver

# Mock mode for development without hardware
MOCK_MODE = True

try:
    import spidev
    MOCK_MODE = False
except ImportError:
    logging.warning("spidev not available, running in MOCK mode")


class ACS712Driver(SensorDriver):
    """Driver for ACS712 current sensor via MCP3008 ADC."""
    
    def __init__(self, sensor_id: int, config: Dict[str, Any]):
        """
        Initialize ACS712 driver.
        
        Args:
            sensor_id: Unique sensor identifier
            config: Configuration dict with keys:
                - adc_driver: ADC chip name (mcp3008)
                - adc_channel: ADC channel number (0-7)
                - spi_bus: SPI bus number (default 0)
                - spi_device: SPI device number (default 1)
                - sensor_range: Sensor range in Amperes (5, 20, 30)
                - calibration_offset: Voltage offset for zero current (V)
                - reference_voltage: ADC reference voltage (V)
        """
        super().__init__(sensor_id, config)
        
        self.adc_channel = config.get('adc_channel', 0)
        self.spi_bus = config.get('spi_bus', 0)
        self.spi_device = config.get('spi_device', 1)
        self.sensor_range = config.get('sensor_range', 30)
        self.calibration_offset = config.get('calibration_offset', 2.5)
        self.reference_voltage = config.get('reference_voltage', 3.3)
        
        # Sensitivity based on sensor model (mV/A)
        sensitivity_map = {5: 185, 20: 100, 30: 66}
        self.sensitivity = sensitivity_map.get(self.sensor_range, 66) / 1000.0  # V/A
        
        self.spi = None
        self.mock_current_base = 10.0
        
    def initialize(self) -> bool:
        """Initialize ACS712 sensor via MCP3008 ADC."""
        try:
            if MOCK_MODE:
                self.logger.info(f"ACS712 (MOCK) initialized on sensor {self.sensor_id}")
                self.is_initialized = True
                return True
            
            # Initialize SPI for MCP3008
            self.spi = spidev.SpiDev()
            self.spi.open(self.spi_bus, self.spi_device)
            
            # SPI settings for MCP3008
            self.spi.max_speed_hz = 1350000  # 1.35 MHz
            self.spi.mode = 0  # CPOL=0, CPHA=0
            
            self.is_initialized = True
            self.logger.info(f"ACS712 (±{self.sensor_range}A) initialized on "
                           f"SPI {self.spi_bus}.{self.spi_device}, channel {self.adc_channel}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ACS712: {e}")
            self.increment_error_count()
            return False
    
    def read_raw(self) -> Optional[Dict[str, Any]]:
        """
        Read current data (single sample).
        
        Returns:
            Dictionary with keys: timestamp, voltage, current, unit
        """
        try:
            if MOCK_MODE:
                return self._read_mock_data()
            
            if not self.is_initialized:
                self.logger.error("Sensor not initialized")
                return None
            
            # Read ADC value
            adc_value = self._read_adc_channel(self.adc_channel)
            
            # Convert to voltage
            voltage = (adc_value / 1023.0) * self.reference_voltage
            
            # Convert to current
            current = (voltage - self.calibration_offset) / self.sensitivity
            
            result = {
                'timestamp': time.time(),
                'voltage': round(voltage, 3),
                'current': round(abs(current), 3),
                'unit': 'ampere'
            }
            
            self.reset_error_count()
            return result
            
        except Exception as e:
            self.logger.error(f"Error reading ACS712: {e}")
            self.increment_error_count()
            return None
    
    def read_rms_current(self, num_samples: int = 100, sample_interval: float = 0.001) -> Optional[float]:
        """
        Read RMS current by sampling over time.
        
        Args:
            num_samples: Number of samples to collect
            sample_interval: Time between samples in seconds
            
        Returns:
            RMS current value in Amperes
        """
        try:
            samples = []
            
            for _ in range(num_samples):
                reading = self.read_raw()
                if reading:
                    samples.append(reading['current'])
                time.sleep(sample_interval)
            
            if not samples:
                return None
            
            # Calculate RMS
            sum_squares = sum(x**2 for x in samples)
            rms = math.sqrt(sum_squares / len(samples))
            
            return round(rms, 3)
            
        except Exception as e:
            self.logger.error(f"Error calculating RMS current: {e}")
            return None
    
    def close(self):
        """Close SPI connection."""
        if self.spi and not MOCK_MODE:
            self.spi.close()
        self.is_initialized = False
        self.logger.info("ACS712 closed")
    
    def _read_adc_channel(self, channel: int) -> int:
        """
        Read MCP3008 ADC channel value.
        
        Args:
            channel: ADC channel (0-7)
            
        Returns:
            10-bit ADC value (0-1023)
        """
        if channel < 0 or channel > 7:
            raise ValueError(f"Invalid ADC channel: {channel}")
        
        # MCP3008 command: start bit + single-ended + channel
        cmd = [1, (8 + channel) << 4, 0]
        
        # Send command and read response
        response = self.spi.xfer2(cmd)
        
        # Extract 10-bit value from response
        adc_value = ((response[1] & 3) << 8) | response[2]
        
        return adc_value
    
    def _read_mock_data(self) -> Dict[str, Any]:
        """Generate mock current data for testing."""
        import random
        
        # Simulate realistic current with gradual changes
        self.mock_current_base += random.uniform(-0.5, 0.5)
        
        # Keep current in realistic range (5-20A)
        self.mock_current_base = max(5.0, min(20.0, self.mock_current_base))
        
        # Add small noise
        current = self.mock_current_base + random.uniform(-0.2, 0.2)
        
        # Calculate voltage
        voltage = self.calibration_offset + (current * self.sensitivity)
        
        return {
            'timestamp': time.time(),
            'voltage': round(voltage, 3),
            'current': round(abs(current), 3),
            'unit': 'ampere'
        }
