# 🔧 Real Hardware Setup Guide

**For UnitaPresidioMacchina001 - Raspberry Pi 4 Model B**

This guide is for setting up the actual production sensors tested on your Raspberry Pi.

---

## 📋 Hardware Configuration

### Raspberry Pi
- **Model**: Raspberry Pi 4 Model B
- **OS**: Raspberry Pi OS (Python 3.13)
- **Hostname**: `UnitaPresidioMacchina001`
- **I2C**: Enabled (bus 1)
- **SPI**: Enabled (bus 0)

---

## 🔌 Sensor Connections

### 1. ISM330DHCX (Accelerometer + Gyroscope)

**Adafruit ISM330DHCX 6-Axis IMU**

**Specifications:**
- I2C address: `0x6A` (SDO/SA0 → GND)
- Accelerometer: ±2/±4/±8/±16 g
- Gyroscope: ±125/±250/±500/±1000/±2000 dps
- Max sampling rate: 6.66 kHz (for FFT analysis)

**Pin Connections:**
| ISM330DHCX | Raspberry Pi | Pin # |
|------------|--------------|-------|
| VIN        | 3.3V         | 17    |
| GND        | GND          | 9     |
| SDA        | GPIO2 (SDA)  | 3     |
| SCL        | GPIO3 (SCL)  | 5     |
| (SDO/SA0)  | GND          | -     |

**Configuration:**
```json
{
  "address": "0x6A",
  "bus": 1,
  "accel_range": 4,
  "gyro_range": 250,
  "sampling_rate": 104,
  "enable_gyro": true
}
```

**Test Command:**
```bash
sudo i2cdetect -y 1
# Should show 0x6A
```

---

### 2. MAX6675 (K-Type Thermocouple)

**MAX6675 Cold-Junction-Compensated K-Thermocouple-to-Digital Converter**

**Specifications:**
- Interface: SPI (read-only)
- Temperature range: 0°C to +1024°C
- Resolution: 0.25°C (12-bit)
- SPI clock: max 4.3 MHz (using 1 MHz)

**Pin Connections:**
| MAX6675 | Raspberry Pi | Pin # | GPIO  |
|---------|--------------|-------|-------|
| VCC     | 3.3V         | 1     | -     |
| GND     | GND          | 6     | -     |
| SO      | MISO         | 21    | GPIO9 |
| SCK     | SCLK         | 23    | GPIO11|
| CS      | CE0          | 24    | GPIO8 |

**Configuration:**
```json
{
  "cs_pin": 0,
  "bus": 0,
  "max_speed_hz": 1000000
}
```

**Test Command:**
```bash
ls -l /dev/spidev0.0
# Should exist

# Python test
python3 << EOF
import spidev
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000
raw = spi.xfer2([0x00, 0x00])
temp = ((raw[0] << 8) | raw[1]) >> 3
print(f"Temperature: {temp * 0.25}°C")
spi.close()
EOF
```

---

### 3. SCT-013-030 + ADS1115 (AC Current Sensor)

**SCT-013-030 Non-Invasive Current Sensor + ADS1115 16-bit ADC**

**SCT-013-030 Specifications:**
- Type: Split-core current transformer (clamp)
- Input: 0-30A AC
- Output: 0-1V AC
- Non-invasive installation

**ADS1115 Specifications:**
- I2C address: `0x48` (ADDR → GND)
- Resolution: 16-bit
- Voltage range: ±0.256V to ±6.144V (using ±4.096V)
- Sample rate: up to 860 SPS

**Bias Circuit (Required for AC signal):**
```
SCT-013 Output → [10kΩ to VDD] → [10kΩ to GND] → [100µF to GND] → ADS1115 A0
                       ↑
                  Bias point (VDD/2 = 1.65V)
```

**Pin Connections:**

*ADS1115:*
| ADS1115 | Raspberry Pi | Pin # |
|---------|--------------|-------|
| VDD     | 3.3V         | 17    |
| GND     | GND          | 20    |
| SDA     | GPIO2 (SDA)  | 3     |
| SCL     | GPIO3 (SCL)  | 5     |
| A0      | Bias circuit | -     |

*SCT-013-030:*
- Connect output to bias circuit
- Clamp around motor power cable (single phase)

**Configuration:**
```json
{
  "address": "0x48",
  "bus": 1,
  "channel": 0,
  "gain": 512,
  "current_range": 30.0,
  "bias_voltage": 1.65,
  "calibration_offset": 0.0,
  "samples_per_read": 100
}
```

**Test Command:**
```bash
sudo i2cdetect -y 1
# Should show 0x48 and 0x6A

# Python test
python3 << EOF
import smbus2, time
bus = smbus2.SMBus(1)
ADDR = 0x48
config = 0xC383  # A0, ±4.096V, single-shot
bus.write_i2c_block_data(ADDR, 0x01, [(config >> 8) & 0xFF, config & 0xFF])
time.sleep(0.01)
data = bus.read_i2c_block_data(ADDR, 0x00, 2)
raw = (data[0] << 8) | data[1]
if raw > 32767:
    raw -= 65536
voltage = raw * 4.096 / 32768
print(f"Voltage: {voltage:.4f}V")
bus.close()
EOF
```

---

## 🧪 Testing

### Quick I2C Scan
```bash
sudo i2cdetect -y 1
```

Expected output:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- 48 -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- 6a -- -- -- -- --
70: -- -- -- -- -- -- -- --

0x6A = ISM330DHCX
0x48 = ADS1115
```

### Run Full Test Suite
```bash
cd /home/pi/rpi-edge-client
source venv/bin/activate
python3 tests/test_real_sensors.py
```

Expected output:
```
==============================================================
VIBRASENSE REAL HARDWARE TEST SUITE
UnitaPresidioMacchina001 - Raspberry Pi 4 Model B
==============================================================

TEST 1: ISM330DHCX (6-axis IMU)
✅ Sensor initialized
  Sample 1: Accel(+0.943, +0.057, +0.369)g Gyro(+1.56, -0.43, +0.26)dps
  ...
✅ TEST PASSED

TEST 2: MAX6675 (K-Type Thermocouple)
✅ Sensor initialized
  Sample 1: 29.50°C (raw: 0x03b0)
  ...
✅ TEST PASSED

TEST 3: SCT-013-030 + ADS1115 (Current Sensor)
✅ Sensor initialized
  Sample 1: 8.234A RMS (bias: 1.6512V)
  ...
✅ TEST PASSED

==============================================================
TEST SUMMARY
==============================================================
  i2c_scan            : ✅ PASSED
  ism330dhcx          : ✅ PASSED
  max6675             : ✅ PASSED
  sct013_ads1115      : ✅ PASSED

Total: 4/4 tests passed

🎉 All tests PASSED! Hardware is ready for production.
```

---

## 📝 Configuration Files

### Use Real Sensors Config

Copy the production configuration:
```bash
cd /home/pi/rpi-edge-client
cp config/sensors.real.json config/sensors.json
```

### Edit Machine Info
```bash
nano config/config.json
```

Set correct IDs:
```json
{
  "device": {
    "device_id": "UnitaPresidioMacchina001",
    "machine_id": 1,
    "company_id": 1
  }
}
```

---

## 🚀 Start Production System

```bash
sudo systemctl start vibrasense-edge
sudo systemctl status vibrasense-edge
sudo journalctl -u vibrasense-edge -f
```

Expected log output:
```
Sensor 1: ISM330DHCX detected (WHO_AM_I: 0x6b)
Sensor 1: Accelerometer configured: ±4g, 104Hz
Sensor 1: Gyroscope configured: ±250dps, 104Hz
Sensor 2: MAX6675 initialized on SPI0.0, 1000000 Hz
Sensor 2: Initial temperature: 29.50°C
Sensor 3: ADS1115 detected at 0x48
Sensor 3: SCT-013-030 + ADS1115 initialized
✓ All sensors initialized
✓ MQTT Client connected
✓ Acquisition started
```

---

## ⚠️ Troubleshooting

### ISM330DHCX not detected

**Check I2C:**
```bash
sudo i2cdetect -y 1
groups pi  # Should include 'i2c'
```

**If missing from group:**
```bash
sudo usermod -aG i2c pi
sudo reboot
```

**Check connections:**
- VIN → 3.3V (NOT 5V!)
- SDA → GPIO2
- SCL → GPIO3
- GND → GND

### MAX6675 open circuit error

**Check SPI:**
```bash
ls -l /dev/spidev*
groups pi  # Should include 'spi'
```

**Check connections:**
- SO → GPIO9 (MISO)
- SCK → GPIO11 (SCLK)
- CS → GPIO8 (CE0)
- Thermocouple properly connected (polarity matters!)

### ADS1115 unstable readings

**⚠️ Pin soldering issue:**
The test data shows: *"I pin dell'ADS1115 non sono ancora saldati, quindi le letture sono instabili per contatto precario. Saldatore in arrivo."*

**Solution:**
- Solder all ADS1115 pins properly
- Check bias circuit (2x 10kΩ + 100µF)
- Verify SCT-013 connection

**After soldering, re-test:**
```bash
python3 tests/test_real_sensors.py
```

---

## 📚 Driver Documentation

### ISM330DHCX Driver
```python
from drivers.ism330dhcx import ISM330DHCXDriver

sensor = ISM330DHCXDriver(1, {
    'address': '0x6A',
    'bus': 1,
    'accel_range': 4,
    'gyro_range': 250,
    'sampling_rate': 104,
    'enable_gyro': True
})

sensor.initialize()
data = sensor.read_raw()
# Returns: {'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z', 'timestamp'}

# For FFT analysis:
burst = sensor.read_burst(num_samples=4096)
```

### MAX6675 Driver
```python
from drivers.max6675 import MAX6675Driver

sensor = MAX6675Driver(2, {
    'cs_pin': 0,
    'bus': 0,
    'max_speed_hz': 1000000
})

sensor.initialize()
data = sensor.read_raw()
# Returns: {'temperature', 'open_circuit', 'timestamp'}
```

### SCT-013 + ADS1115 Driver
```python
from drivers.sct013_ads1115 import SCT013ADS1115Driver

sensor = SCT013ADS1115Driver(3, {
    'address': '0x48',
    'bus': 1,
    'channel': 0,
    'current_range': 30.0,
    'bias_voltage': 1.65,
    'samples_per_read': 100
})

sensor.initialize()
data = sensor.read_raw()
# Returns: {'current' (RMS), 'voltage_bias', 'timestamp'}
```

---

## 🎯 Next Steps

1. ✅ Complete ADS1115 pin soldering
2. ✅ Run full test suite
3. ✅ Configure MQTT broker credentials
4. ✅ Start production system
5. ✅ Monitor for 24 hours
6. ✅ Set up dashboard

---

**Last Updated**: 2026-03-27  
**Hardware Version**: UnitaPresidioMacchina001  
**Tested By**: iltempoprezioso
