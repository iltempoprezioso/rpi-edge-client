#!/usr/bin/env python3
"""
ISM330DHCX 6-axis IMU Driver (Accelerometer + Gyroscope)
I2C interface, addresses 0x6A (SDO=GND) or 0x6B (SDO=VDD)
Datasheet: https://www.st.com/resource/en/datasheet/ism330dhcx.pdf
"""

import time
import struct
import logging
from typing import Dict, Optional

try:
    import smbus2
    SMBUS2_AVAILABLE = True
except ImportError:
    SMBUS2_AVAILABLE = False

from drivers.base_driver import SensorDriver
from drivers.retry_utils import i2c_retry

logger = logging.getLogger(__name__)


class ISM330DHCXDriver(SensorDriver):
    """
    Driver for ISM330DHCX 6-axis IMU
    
    Features:
    - 3-axis accelerometer: ±2/±4/±8/±16 g
    - 3-axis gyroscope: ±125/±250/±500/±1000/±2000 dps
    - Sampling rate: up to 6.66 kHz
    - I2C interface
    
    Tested configuration:
    - Accelerometer: 104 Hz, ±4g
    - Gyroscope: 104 Hz, ±250 dps
    - High-frequency mode: 6.66 kHz for FFT analysis
    """
    
    # I2C addresses
    I2C_ADDR_SDO_GND = 0x6A  # SDO/SA0 connected to GND
    I2C_ADDR_SDO_VDD = 0x6B  # SDO/SA0 connected to VDD
    
    # Register addresses
    REG_WHO_AM_I = 0x0F
    REG_CTRL1_XL = 0x10  # Accelerometer control
    REG_CTRL2_G = 0x11   # Gyroscope control
    REG_CTRL3_C = 0x12   # Control register 3
    REG_STATUS_REG = 0x1E
    REG_OUTX_L_G = 0x22  # Gyroscope data start
    REG_OUTX_L_A = 0x28  # Accelerometer data start
    
    # FIFO registers (for high-speed burst mode)
    REG_FIFO_CTRL1 = 0x07  # FIFO watermark threshold low
    REG_FIFO_CTRL2 = 0x08  # FIFO watermark threshold high
    REG_FIFO_CTRL3 = 0x09  # FIFO BDR (Batch Data Rate)
    REG_FIFO_CTRL4 = 0x0A  # FIFO mode and decimation
    REG_FIFO_STATUS1 = 0x3A  # FIFO fill level (low byte)
    REG_FIFO_STATUS2 = 0x3B  # FIFO fill level (high byte) + flags
    REG_FIFO_DATA_OUT_TAG = 0x78  # FIFO output tag
    REG_FIFO_DATA_OUT_X_L = 0x79  # FIFO data output start
    
    # WHO_AM_I expected value
    DEVICE_ID = 0x6B
    
    # Accelerometer ranges (g)
    ACCEL_RANGE_2G = 0
    ACCEL_RANGE_4G = 2
    ACCEL_RANGE_8G = 3
    ACCEL_RANGE_16G = 1
    
    # Gyroscope ranges (dps)
    GYRO_RANGE_125 = 1
    GYRO_RANGE_250 = 0
    GYRO_RANGE_500 = 2
    GYRO_RANGE_1000 = 4
    GYRO_RANGE_2000 = 6
    
    # Output Data Rates (Hz)
    ODR_POWER_DOWN = 0x00
    ODR_12_5_HZ = 0x10
    ODR_26_HZ = 0x20
    ODR_52_HZ = 0x30
    ODR_104_HZ = 0x40
    ODR_208_HZ = 0x50
    ODR_416_HZ = 0x60
    ODR_833_HZ = 0x70
    ODR_1660_HZ = 0x80
    ODR_3330_HZ = 0x90
    ODR_6660_HZ = 0xA0
    
    def __init__(self, sensor_id: int, config: Dict):
        """
        Initialize ISM330DHCX driver
        
        Args:
            sensor_id: Unique sensor identifier
            config: Configuration dictionary with:
                - address: I2C address (default 0x6A)
                - bus: I2C bus number (default 1)
                - accel_range: Accelerometer range in g (2, 4, 8, 16)
                - gyro_range: Gyroscope range in dps (125, 250, 500, 1000, 2000)
                - sampling_rate: ODR in Hz (12.5 to 6660)
                - enable_gyro: Enable gyroscope (default True)
        """
        super().__init__(sensor_id, config)
        
        self.i2c_address = int(config.get('address', '0x6A'), 16)
        self.bus_number = config.get('bus', 1)
        self.accel_range = config.get('accel_range', 4)  # ±4g default
        self.gyro_range = config.get('gyro_range', 250)  # ±250 dps default
        self.sampling_rate = config.get('sampling_rate', 104)  # 104 Hz default
        self.enable_gyro = config.get('enable_gyro', True)
        
        self.bus: Optional[smbus2.SMBus] = None
        self.accel_scale = 0.0
        self.gyro_scale = 0.0
        
        # Map ranges to register values and scales
        self.accel_range_map = {
            2: (self.ACCEL_RANGE_2G, 0.061),    # mg/LSB
            4: (self.ACCEL_RANGE_4G, 0.122),
            8: (self.ACCEL_RANGE_8G, 0.244),
            16: (self.ACCEL_RANGE_16G, 0.488),
        }
        
        self.gyro_range_map = {
            125: (self.GYRO_RANGE_125, 4.375),   # mdps/LSB
            250: (self.GYRO_RANGE_250, 8.75),
            500: (self.GYRO_RANGE_500, 17.50),
            1000: (self.GYRO_RANGE_1000, 35.0),
            2000: (self.GYRO_RANGE_2000, 70.0),
        }
        
        self.odr_map = {
            12.5: self.ODR_12_5_HZ,
            26: self.ODR_26_HZ,
            52: self.ODR_52_HZ,
            104: self.ODR_104_HZ,
            208: self.ODR_208_HZ,
            416: self.ODR_416_HZ,
            833: self.ODR_833_HZ,
            1660: self.ODR_1660_HZ,
            3330: self.ODR_3330_HZ,
            6660: self.ODR_6660_HZ,
        }
    
    def initialize(self) -> bool:
        """Initialize I2C connection and configure sensor"""
        try:
            if not SMBUS2_AVAILABLE:
                logger.warning(f"Sensor {self.sensor_id}: smbus2 not available, using mock mode")
                self.mock_mode = True
                return True
            
            # Open I2C bus
            self.bus = smbus2.SMBus(self.bus_number)
            
            # Check WHO_AM_I
            who_am_i = self.bus.read_byte_data(self.i2c_address, self.REG_WHO_AM_I)
            if who_am_i != self.DEVICE_ID:
                logger.error(f"Sensor {self.sensor_id}: Invalid WHO_AM_I: {who_am_i:#04x}, expected {self.DEVICE_ID:#04x}")
                return False
            
            logger.info(f"Sensor {self.sensor_id}: ISM330DHCX detected (WHO_AM_I: {who_am_i:#04x})")
            
            # Software reset
            self.bus.write_byte_data(self.i2c_address, self.REG_CTRL3_C, 0x01)
            time.sleep(0.1)
            
            # Configure accelerometer
            accel_reg_val, self.accel_scale = self.accel_range_map[self.accel_range]
            odr = self._get_odr_value(self.sampling_rate)
            ctrl1_xl = odr | (accel_reg_val << 2)
            self.bus.write_byte_data(self.i2c_address, self.REG_CTRL1_XL, ctrl1_xl)
            
            logger.info(f"Sensor {self.sensor_id}: Accelerometer configured: ±{self.accel_range}g, {self.sampling_rate}Hz")
            
            # Configure gyroscope
            if self.enable_gyro:
                gyro_reg_val, self.gyro_scale = self.gyro_range_map[self.gyro_range]
                ctrl2_g = odr | (gyro_reg_val << 2)
                self.bus.write_byte_data(self.i2c_address, self.REG_CTRL2_G, ctrl2_g)
                logger.info(f"Sensor {self.sensor_id}: Gyroscope configured: ±{self.gyro_range}dps, {self.sampling_rate}Hz")
            else:
                # Power down gyroscope
                self.bus.write_byte_data(self.i2c_address, self.REG_CTRL2_G, 0x00)
            
            # Wait for first data
            time.sleep(0.05)
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Sensor {self.sensor_id}: Initialization failed: {e}")
            return False
    
    def _get_odr_value(self, rate: float) -> int:
        """Get ODR register value for requested sampling rate"""
        # Find closest available rate
        available_rates = list(self.odr_map.keys())
        closest_rate = min(available_rates, key=lambda x: abs(x - rate))
        
        if closest_rate != rate:
            logger.warning(f"Sensor {self.sensor_id}: Requested {rate}Hz, using {closest_rate}Hz")
        
        return self.odr_map[closest_rate]
    
    @i2c_retry(max_retries=3, delay=0.05)
    def read_raw(self) -> Dict:
        """
        Read raw accelerometer and gyroscope data
        
        Returns:
            Dictionary with:
            - accel_x, accel_y, accel_z: acceleration in g
            - gyro_x, gyro_y, gyro_z: angular rate in dps (if enabled)
            - timestamp: Unix timestamp
        """
        if self.mock_mode:
            return self._generate_mock_data()
        
        try:
            # Read all sensor data in one transaction (12 bytes)
            # Gyroscope: OUTX_L_G (0x22) to OUTZ_H_G (0x27) = 6 bytes
            # Accelerometer: OUTX_L_A (0x28) to OUTZ_H_A (0x2D) = 6 bytes
            data = self.bus.read_i2c_block_data(self.i2c_address, self.REG_OUTX_L_G, 12)
            
            # Unpack gyroscope data (3x int16, little-endian)
            gyro_raw = struct.unpack('<hhh', bytes(data[0:6]))
            
            # Unpack accelerometer data (3x int16, little-endian)
            accel_raw = struct.unpack('<hhh', bytes(data[6:12]))
            
            # Convert to physical units
            result = {
                'accel_x': accel_raw[0] * self.accel_scale / 1000.0,  # mg to g
                'accel_y': accel_raw[1] * self.accel_scale / 1000.0,
                'accel_z': accel_raw[2] * self.accel_scale / 1000.0,
                'timestamp': time.time()
            }
            
            if self.enable_gyro:
                result.update({
                    'gyro_x': gyro_raw[0] * self.gyro_scale / 1000.0,  # mdps to dps
                    'gyro_y': gyro_raw[1] * self.gyro_scale / 1000.0,
                    'gyro_z': gyro_raw[2] * self.gyro_scale / 1000.0,
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Sensor {self.sensor_id}: Read failed: {e}")
            return {'error': str(e), 'timestamp': time.time()}
    
    def _generate_mock_data(self) -> Dict:
        """Generate mock sensor data for testing"""
        import random
        
        result = {
            'accel_x': random.uniform(-0.1, 0.1),
            'accel_y': random.uniform(-0.1, 0.1),
            'accel_z': random.uniform(0.9, 1.1),  # ~1g from gravity
            'timestamp': time.time()
        }
        
        if self.enable_gyro:
            result.update({
                'gyro_x': random.uniform(-2, 2),
                'gyro_y': random.uniform(-2, 2),
                'gyro_z': random.uniform(-2, 2),
            })
        
        return result
    
    def read_burst(self, num_samples: int, delay: float = None, use_fifo: bool = True) -> list:
        """
        Read multiple samples for FFT analysis
        
        Args:
            num_samples: Number of samples to read (e.g., 4096)
            delay: Delay between samples (None = as fast as possible)
            use_fifo: Use hardware FIFO for high-speed acquisition (recommended for FFT)
        
        Returns:
            List of dictionaries with sensor data
        """
        if use_fifo and not self.mock_mode:
            return self._read_burst_fifo(num_samples)
        else:
            # Fallback to slow method (for mock mode or compatibility)
            samples = []
            for _ in range(num_samples):
                samples.append(self.read_raw())
                if delay:
                    time.sleep(delay)
            return samples
    
    def _read_burst_fifo(self, num_samples: int) -> list:
        """
        Read burst using hardware FIFO — fast enough for FFT at 6660 Hz
        
        This method uses the ISM330DHCX's internal 512-sample FIFO buffer
        to achieve true 6660 Hz sampling rate for FFT analysis.
        
        Args:
            num_samples: Number of samples to acquire (e.g., 4096 for FFT)
        
        Returns:
            List of dictionaries with accelerometer data
        """
        if self.mock_mode:
            logger.warning("FIFO mode not available in mock mode")
            return []
        
        try:
            # Save current ODR
            original_odr = self.sampling_rate
            
            # 1. Configure accelerometer for 6660 Hz
            odr_6660 = self.ODR_6660_HZ
            accel_reg_val, _ = self.accel_range_map[self.accel_range]
            ctrl1_xl = odr_6660 | (accel_reg_val << 2)
            self.bus.write_byte_data(self.i2c_address, self.REG_CTRL1_XL, ctrl1_xl)
            
            logger.info(f"Sensor {self.sensor_id}: Starting FIFO burst mode at 6660 Hz for {num_samples} samples")
            
            # 2. Configure FIFO: continuous mode, accelerometer only
            self.bus.write_byte_data(self.i2c_address, self.REG_FIFO_CTRL1, 0x00)  # Watermark low
            self.bus.write_byte_data(self.i2c_address, self.REG_FIFO_CTRL2, 0x00)  # Watermark high
            self.bus.write_byte_data(self.i2c_address, self.REG_FIFO_CTRL3, 0xA0)  # BDR accel = 6660 Hz
            self.bus.write_byte_data(self.i2c_address, self.REG_FIFO_CTRL4, 0x06)  # Continuous mode
            
            time.sleep(0.01)  # Let FIFO start filling
            
            samples = []
            start_time = time.time()
            timeout = num_samples / 6660 * 2  # 2x expected time as timeout
            
            # 3. Read samples from FIFO
            while len(samples) < num_samples:
                # Check timeout
                if time.time() - start_time > timeout:
                    logger.error(f"Sensor {self.sensor_id}: FIFO burst timeout after {len(samples)} samples")
                    break
                
                # Check FIFO fill level
                status1 = self.bus.read_byte_data(self.i2c_address, self.REG_FIFO_STATUS1)
                status2 = self.bus.read_byte_data(self.i2c_address, self.REG_FIFO_STATUS2)
                fifo_count = ((status2 & 0x03) << 8) | status1
                
                if fifo_count == 0:
                    time.sleep(0.001)  # Brief wait for more data
                    continue
                
                # Read available samples (up to remaining needed)
                samples_to_read = min(fifo_count, num_samples - len(samples))
                
                for _ in range(samples_to_read):
                    # Read tag + 6 bytes data (3x int16 for X, Y, Z)
                    data = self.bus.read_i2c_block_data(self.i2c_address, self.REG_FIFO_DATA_OUT_TAG, 7)
                    tag = data[0] >> 3
                    
                    # Tag 0x02 = accelerometer data
                    if tag == 0x02:
                        raw = struct.unpack('<hhh', bytes(data[1:7]))
                        samples.append({
                            'accel_x': raw[0] * self.accel_scale / 1000.0,
                            'accel_y': raw[1] * self.accel_scale / 1000.0,
                            'accel_z': raw[2] * self.accel_scale / 1000.0,
                            'timestamp': time.time()
                        })
            
            # 4. Restore normal ODR and disable FIFO
            odr_normal = self._get_odr_value(original_odr)
            ctrl1_xl = odr_normal | (accel_reg_val << 2)
            self.bus.write_byte_data(self.i2c_address, self.REG_CTRL1_XL, ctrl1_xl)
            self.bus.write_byte_data(self.i2c_address, self.REG_FIFO_CTRL4, 0x00)  # FIFO bypass mode
            
            elapsed = time.time() - start_time
            actual_rate = len(samples) / elapsed if elapsed > 0 else 0
            logger.info(f"Sensor {self.sensor_id}: FIFO burst complete - {len(samples)} samples in {elapsed:.2f}s ({actual_rate:.0f} Hz)")
            
            return samples[:num_samples]
            
        except Exception as e:
            logger.error(f"Sensor {self.sensor_id}: FIFO burst failed: {e}")
            
            # Try to restore normal mode
            try:
                odr_normal = self._get_odr_value(original_odr)
                accel_reg_val, _ = self.accel_range_map[self.accel_range]
                ctrl1_xl = odr_normal | (accel_reg_val << 2)
                self.bus.write_byte_data(self.i2c_address, self.REG_CTRL1_XL, ctrl1_xl)
                self.bus.write_byte_data(self.i2c_address, self.REG_FIFO_CTRL4, 0x00)
            except:
                pass
            
            return []
    
    def get_status(self) -> Dict:
        """Get sensor status"""
        if self.mock_mode:
            return {
                'initialized': True,
                'mock_mode': True,
                'healthy': True
            }
        
        try:
            status = self.bus.read_byte_data(self.i2c_address, self.REG_STATUS_REG)
            
            return {
                'initialized': self.initialized,
                'mock_mode': False,
                'healthy': True,
                'accel_data_ready': bool(status & 0x01),
                'gyro_data_ready': bool(status & 0x02) if self.enable_gyro else None,
                'temperature_data_ready': bool(status & 0x04),
            }
            
        except Exception as e:
            logger.error(f"Sensor {self.sensor_id}: Status check failed: {e}")
            return {
                'initialized': self.initialized,
                'healthy': False,
                'error': str(e)
            }
    
    def shutdown(self) -> bool:
        """Shutdown sensor and close I2C connection"""
        try:
            if not self.mock_mode and self.bus:
                # Power down accelerometer and gyroscope
                self.bus.write_byte_data(self.i2c_address, self.REG_CTRL1_XL, 0x00)
                self.bus.write_byte_data(self.i2c_address, self.REG_CTRL2_G, 0x00)
                self.bus.close()
                logger.info(f"Sensor {self.sensor_id}: Shutdown complete")
            
            self.initialized = False
            return True
            
        except Exception as e:
            logger.error(f"Sensor {self.sensor_id}: Shutdown failed: {e}")
            return False
