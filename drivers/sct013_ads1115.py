#!/usr/bin/env python3
"""
SCT-013-030 Current Sensor + ADS1115 ADC Driver
Non-invasive AC current sensor (clamp) with 16-bit ADC
SCT-013-030: 30A input → 1V AC output
ADS1115: 16-bit ADC, I2C interface, ±4.096V range
"""

import time
import math
import logging
from typing import Dict, Optional, List

try:
    import smbus2
    SMBUS2_AVAILABLE = True
except ImportError:
    SMBUS2_AVAILABLE = False

from drivers.base_driver import SensorDriver
from drivers.retry_utils import i2c_retry

logger = logging.getLogger(__name__)


class SCT013ADS1115Driver(SensorDriver):
    """
    Driver for SCT-013-030 current sensor + ADS1115 ADC
    
    Hardware setup:
    - SCT-013-030 output → Bias circuit (2x 10kΩ + 100µF)
    - Bias circuit output → ADS1115 A0
    - Bias voltage: VDD/2 (1.65V for 3.3V VDD)
    
    Features:
    - Current range: 0-30A AC
    - Resolution: 16-bit (15-bit signed)
    - Sampling: up to 860 SPS
    - RMS calculation for AC current
    
    Tested configuration:
    - I2C address: 0x48
    - Gain: ±4.096V
    - Sample rate: 128 SPS (single-shot mode)
    - Bias voltage: 1.65V (for AC signal centering)
    """
    
    # I2C addresses (configurable via ADDR pin)
    I2C_ADDR_GND = 0x48  # ADDR → GND (default)
    I2C_ADDR_VDD = 0x49  # ADDR → VDD
    I2C_ADDR_SDA = 0x4A  # ADDR → SDA
    I2C_ADDR_SCL = 0x4B  # ADDR → SCL
    
    # Register addresses
    REG_CONVERSION = 0x00
    REG_CONFIG = 0x01
    REG_LO_THRESH = 0x02
    REG_HI_THRESH = 0x03
    
    # Config register bits
    # OS: Operational status (bit 15)
    OS_SINGLE_SHOT = 0x8000
    
    # MUX: Input multiplexer (bits 14-12)
    MUX_AIN0_GND = 0x4000  # A0 vs GND
    MUX_AIN1_GND = 0x5000  # A1 vs GND
    MUX_AIN2_GND = 0x6000  # A2 vs GND
    MUX_AIN3_GND = 0x7000  # A3 vs GND
    
    # PGA: Programmable gain amplifier (bits 11-9)
    PGA_6_144V = 0x0000  # ±6.144V
    PGA_4_096V = 0x0200  # ±4.096V (default)
    PGA_2_048V = 0x0400  # ±2.048V
    PGA_1_024V = 0x0600  # ±1.024V
    PGA_0_512V = 0x0800  # ±0.512V
    PGA_0_256V = 0x0A00  # ±0.256V
    
    # MODE: Device operating mode (bit 8)
    MODE_CONTINUOUS = 0x0000
    MODE_SINGLE_SHOT = 0x0100
    
    # DR: Data rate (bits 7-5)
    DR_8_SPS = 0x0000
    DR_16_SPS = 0x0020
    DR_32_SPS = 0x0040
    DR_64_SPS = 0x0060
    DR_128_SPS = 0x0080  # Default
    DR_250_SPS = 0x00A0
    DR_475_SPS = 0x00C0
    DR_860_SPS = 0x00E0
    
    # COMP_MODE, COMP_POL, COMP_LAT, COMP_QUE (bits 4-0)
    COMP_DEFAULT = 0x0003  # Disable comparator
    
    # Voltage ranges for each PGA setting
    PGA_RANGES = {
        0x0000: 6.144,
        0x0200: 4.096,
        0x0400: 2.048,
        0x0600: 1.024,
        0x0800: 0.512,
        0x0A00: 0.256,
    }
    
    def __init__(self, sensor_id: int, config: Dict):
        """
        Initialize SCT-013 + ADS1115 driver
        
        Args:
            sensor_id: Unique sensor identifier
            config: Configuration dictionary with:
                - address: I2C address (default 0x48)
                - bus: I2C bus number (default 1)
                - channel: ADC channel (0-3, default 0)
                - gain: PGA gain setting (default ±4.096V)
                - current_range: Max current in A (default 30)
                - bias_voltage: Bias voltage in V (default 1.65)
                - calibration_offset: Calibration offset in A (default 0)
                - samples_per_read: Number of samples for RMS calculation (default 100)
        """
        super().__init__(sensor_id, config)
        
        self.i2c_address = int(config.get('address', '0x48'), 16)
        self.bus_number = config.get('bus', 1)
        self.channel = config.get('channel', 0)
        
        # Parse gain (support both string "4.096V" and int 512/0x0200)
        gain_config = config.get('gain', '4.096V')
        self.gain = self._parse_gain(gain_config)
        
        self.current_range = config.get('current_range', 30.0)  # 30A for SCT-013-030
        self.bias_voltage = config.get('bias_voltage', 1.65)  # VDD/2
        self.calibration_offset = config.get('calibration_offset', 0.0)
        self.samples_per_read = config.get('samples_per_read', 100)
        
        self.bus: Optional[smbus2.SMBus] = None
        self.voltage_range = self.PGA_RANGES.get(self.gain, 4.096)
        
        # SCT-013-030: 30A → 1V output
        # Current (A) = (Voltage - Bias) / (1V / 30A) = (Voltage - Bias) * 30
        self.voltage_to_current = self.current_range  # 30 A/V
        
        # Channel MUX settings
        self.mux_channels = {
            0: self.MUX_AIN0_GND,
            1: self.MUX_AIN1_GND,
            2: self.MUX_AIN2_GND,
            3: self.MUX_AIN3_GND,
        }
        
        # Gain string to constant mapping
        self.gain_str_map = {
            '6.144V': self.PGA_6_144V,
            '4.096V': self.PGA_4_096V,
            '2.048V': self.PGA_2_048V,
            '1.024V': self.PGA_1_024V,
            '0.512V': self.PGA_0_512V,
            '0.256V': self.PGA_0_256V,
        }
    
    def _parse_gain(self, gain_config):
        """
        Parse gain configuration (supports string or int)
        
        Args:
            gain_config: Either a string like "4.096V" or an int like 512 (0x0200)
        
        Returns:
            PGA register value
        """
        if isinstance(gain_config, str):
            # String format: "4.096V"
            if gain_config in self.gain_str_map:
                return self.gain_str_map[gain_config]
            else:
                logger.warning(f"Sensor {self.sensor_id}: Unknown gain '{gain_config}', using 4.096V")
                return self.PGA_4_096V
        else:
            # Integer format: 512 or 0x0200
            return gain_config
    
    def initialize(self) -> bool:
        """Initialize I2C connection and configure ADC"""
        try:
            if not SMBUS2_AVAILABLE:
                logger.warning(f"Sensor {self.sensor_id}: smbus2 not available, using mock mode")
                self.mock_mode = True
                return True
            
            # Open I2C bus
            self.bus = smbus2.SMBus(self.bus_number)
            
            # Test read config register
            try:
                config_bytes = self.bus.read_i2c_block_data(self.i2c_address, self.REG_CONFIG, 2)
                logger.info(f"Sensor {self.sensor_id}: ADS1115 detected at 0x{self.i2c_address:02x}")
            except:
                logger.error(f"Sensor {self.sensor_id}: ADS1115 not found at 0x{self.i2c_address:02x}")
                return False
            
            logger.info(f"Sensor {self.sensor_id}: SCT-013-030 + ADS1115 initialized")
            logger.info(f"  - Channel: A{self.channel}")
            logger.info(f"  - Range: ±{self.voltage_range}V → 0-{self.current_range}A")
            logger.info(f"  - Bias voltage: {self.bias_voltage}V")
            logger.info(f"  - Samples per RMS: {self.samples_per_read}")
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Sensor {self.sensor_id}: Initialization failed: {e}")
            return False
    
    @i2c_retry(max_retries=3, delay=0.05)
    def _read_adc_single(self) -> Optional[float]:
        """
        Read single ADC sample
        
        Returns:
            Voltage in V, or None on error
        """
        try:
            # Build config register
            config = (
                self.OS_SINGLE_SHOT |
                self.mux_channels[self.channel] |
                self.gain |
                self.MODE_SINGLE_SHOT |
                self.DR_128_SPS |
                self.COMP_DEFAULT
            )
            
            # Write config to start conversion
            config_bytes = [(config >> 8) & 0xFF, config & 0xFF]
            self.bus.write_i2c_block_data(self.i2c_address, self.REG_CONFIG, config_bytes)
            
            # Wait for conversion (at 128 SPS, max 8ms)
            time.sleep(0.01)
            
            # Read conversion result
            data = self.bus.read_i2c_block_data(self.i2c_address, self.REG_CONVERSION, 2)
            raw = (data[0] << 8) | data[1]
            
            # Convert to signed 16-bit
            if raw > 32767:
                raw -= 65536
            
            # Convert to voltage
            voltage = raw * self.voltage_range / 32768.0
            
            return voltage
            
        except Exception as e:
            logger.error(f"Sensor {self.sensor_id}: ADC read failed: {e}")
            return None
    
    def _read_rms_current(self) -> Optional[float]:
        """
        Read multiple samples and calculate RMS current
        
        For AC current measurement, we need to:
        1. Sample the signal multiple times
        2. Calculate RMS value
        3. Convert voltage to current
        
        Returns:
            RMS current in A, or None on error
        """
        samples: List[float] = []
        
        for _ in range(self.samples_per_read):
            voltage = self._read_adc_single()
            if voltage is None:
                continue
            
            # Remove bias voltage
            voltage_ac = voltage - self.bias_voltage
            
            # Convert to current (instantaneous)
            current_inst = voltage_ac * self.voltage_to_current
            
            samples.append(current_inst)
        
        if len(samples) < self.samples_per_read * 0.5:
            logger.error(f"Sensor {self.sensor_id}: Too many failed samples")
            return None
        
        # Calculate RMS
        sum_squares = sum(i**2 for i in samples)
        rms_current = math.sqrt(sum_squares / len(samples))
        
        # Apply calibration offset
        rms_current -= self.calibration_offset
        
        # Ensure non-negative
        if rms_current < 0:
            rms_current = 0.0
        
        return rms_current
    
    def read_raw(self) -> Dict:
        """
        Read RMS current from SCT-013
        
        Returns:
            Dictionary with:
            - current: RMS current in A
            - voltage_bias: Measured bias voltage
            - timestamp: Unix timestamp
        """
        if self.mock_mode:
            return self._generate_mock_data()
        
        try:
            # Read RMS current
            rms_current = self._read_rms_current()
            
            if rms_current is None:
                return {
                    'error': 'RMS calculation failed',
                    'timestamp': time.time()
                }
            
            # Also read bias voltage (for diagnostics)
            bias_voltage_measured = self._read_adc_single()
            
            return {
                'current': round(rms_current, 3),
                'voltage_bias': round(bias_voltage_measured, 4) if bias_voltage_measured else None,
                'samples': self.samples_per_read,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Sensor {self.sensor_id}: Read failed: {e}")
            return {
                'error': str(e),
                'timestamp': time.time()
            }
    
    def _generate_mock_data(self) -> Dict:
        """Generate mock current data for testing"""
        import random
        
        # Simulate typical motor current with small fluctuations
        base_current = 8.0  # Amps
        current = base_current + random.uniform(-1.0, 1.0)
        
        return {
            'current': round(max(0, current), 3),
            'voltage_bias': 1.65,
            'samples': self.samples_per_read,
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
            
            healthy = 'error' not in data
            
            return {
                'initialized': self.initialized,
                'mock_mode': False,
                'healthy': healthy,
                'last_current': data.get('current'),
                'bias_voltage': data.get('voltage_bias')
            }
            
        except Exception as e:
            logger.error(f"Sensor {self.sensor_id}: Status check failed: {e}")
            return {
                'initialized': self.initialized,
                'healthy': False,
                'error': str(e)
            }
    
    def shutdown(self) -> bool:
        """Close I2C connection"""
        try:
            if not self.mock_mode and self.bus:
                self.bus.close()
                logger.info(f"Sensor {self.sensor_id}: I2C closed")
            
            self.initialized = False
            return True
            
        except Exception as e:
            logger.error(f"Sensor {self.sensor_id}: Shutdown failed: {e}")
            return False
