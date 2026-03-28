# VibraSense Edge Client

**Industrial IoT Edge Software for Raspberry Pi**

Real-time sensor monitoring and data acquisition system for predictive maintenance of industrial machinery.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## 📋 Overview

VibraSense Edge Client is a production-ready edge computing software for Raspberry Pi that:

- **Acquires data** from industrial sensors (vibration, temperature, current)
- **Pre-processes** signals with digital filters and RMS calculations
- **Transmits** data to cloud via MQTT with TLS encryption
- **Buffers** locally using SQLite for resilience during network outages
- **Supports remote management** via MQTT commands (start/stop/update/reboot)
- **Auto-recovers** from failures with built-in watchdog
- **Updates remotely** with automatic backup and rollback

---

## 🎯 Features

### Data Acquisition
- ✅ 3+ simultaneous sensors per machine
- ✅ Configurable sampling rates (100-1600 Hz for vibrations)
- ✅ I2C, SPI, and ADC interfaces
- ✅ Mock mode for development without hardware

### WiFi Setup (NEW! 📱)
- ✅ **Captive Portal** for smartphone-based WiFi configuration
- ✅ **Plug-and-play** setup without monitor/keyboard
- ✅ **Auto-fallback** to hotspot if WiFi connection lost
- ✅ **QR code** for quick smartphone connection
- ✅ First-time setup in 5 minutes via smartphone

### Supported Sensors

**Production Hardware (Tested on UnitaPresidioMacchina001):**
| Sensor | Type | Interface | Range | Notes |
|--------|------|-----------|-------|-------|
| ISM330DHCX | 6-axis IMU (accel+gyro) | I2C (0x6A) | ±4g, ±250dps | High-speed 6.66kHz for FFT |
| MAX6675 | K-type thermocouple | SPI CE0 | 0-1024°C | 0.25°C resolution |
| SCT-013-030 + ADS1115 | AC current (clamp) | I2C (0x48) | 0-30A | Non-invasive, RMS calc |

**Legacy/Alternative Sensors (drivers available):**
| Sensor | Type | Interface | Range |
|--------|------|-----------|-------|
| ADXL345 | 3-axis accelerometer | I2C | ±16g |
| MAX31855 | K-type thermocouple | SPI | -200°C to +1350°C |
| ACS712 | Hall effect current | ADC (MCP3008) | 0-30A |

### Signal Processing
- High-pass filter (1 Hz cutoff, DC offset removal)
- Low-pass filter (500 Hz cutoff, anti-aliasing)
- Notch filter (50/60 Hz, power line rejection)
- RMS, peak-to-peak, and peak calculations
- FFT spectrum analysis (ready for v1.1)

### Communication
- MQTT v3.1.1 with TLS 1.2+
- QoS 0/1 for different message types
- Automatic reconnection and retry
- Configurable topics: readings, status, heartbeat, commands

### Resilience
- SQLite buffer for up to 70,000 readings (~7 days)
- Automatic retry of failed transmissions
- Network connectivity monitoring
- Sensor health checks and auto-recovery
- Watchdog with heartbeat (every 60s)

### Remote Management
- START/STOP acquisition
- Update configuration
- Software update via Git pull
- Automatic backup before updates
- Rollback on failure
- System reboot
- Status queries

---

## 🚀 Quick Start

### Prerequisites

**Hardware:**
- Raspberry Pi 4 Model B (2GB+ RAM) or Raspberry Pi 5
- microSD card 32GB+ (Class 10)
- Power supply 5V 3A (official recommended)

**Software:**
- Raspberry Pi OS Lite (64-bit, Debian 12 Bookworm)
- Internet connection for initial setup

### Installation

1. **Flash Raspberry Pi OS:**
   ```bash
   # Use Raspberry Pi Imager
   # Enable SSH, set hostname: vibrasense-rpi-001
   # WiFi configuration optional (can be done via captive portal)
   ```

2. **Clone repository:**
   ```bash
   ssh pi@vibrasense-rpi-001.local
   cd /home/pi
   git clone https://github.com/vibrasense/rpi-edge-client.git
   cd rpi-edge-client
   ```

3. **Run installation script:**
   ```bash
   chmod +x scripts/install.sh
   ./scripts/install.sh
   # Choose 'Y' when asked about captive portal (recommended)
   ```

4. **Configure (if not using captive portal):**
   ```bash
   nano config/config.json
   nano config/mqtt.json
   nano config/sensors.json
   ```

5. **Start service:**
   ```bash
   sudo systemctl start vibrasense-edge
   sudo systemctl status vibrasense-edge
   ```

6. **First-time WiFi setup (if captive portal enabled):**
   - Connect smartphone to `VibraSense-Setup-XXX` hotspot
   - Password: `vibrasense2026`
   - Browser opens automatically with configuration page
   - Enter your office WiFi credentials
   - Device connects and starts working automatically

7. **Check logs:**
   ```bash
   sudo journalctl -u vibrasense-edge -f
   # or
   tail -f logs/vibrasense.log
   ```

---

## 📁 Project Structure

```
rpi-edge-client/
├── config/
│   ├── config.example.json          # Main configuration
│   ├── mqtt.example.json            # MQTT broker settings
│   └── sensors.example.json         # Sensor definitions
├── src/
│   ├── main.py                      # Application entry point
│   ├── sensor_manager.py            # Sensor orchestration
│   ├── mqtt_client.py               # MQTT communication
│   ├── buffer_manager.py            # SQLite buffering
│   ├── data_processor.py            # Signal processing
│   ├── command_handler.py           # Remote commands
│   ├── watchdog.py                  # Health monitoring
│   └── update_manager.py            # Software updates
├── drivers/
│   ├── base_driver.py               # Driver interface
│   ├── adxl345.py                   # Accelerometer driver
│   ├── max31855.py                  # Thermocouple driver
│   └── acs712.py                    # Current sensor driver
├── tests/
│   └── test_components.py           # Component tests
├── scripts/
│   └── install.sh                   # Installation script
├── docs/
│   └── (documentation files)
├── requirements.txt                 # Python dependencies
├── vibrasense-edge.service          # Systemd service
└── README.md                        # This file
```

---

## ⚙️ Configuration

### Main Configuration (`config/config.json`)

```json
{
  "device": {
    "device_id": "rpi-001",
    "machine_id": 1,
    "company_id": 1
  },
  "acquisition": {
    "read_interval": 600,
    "enabled": true,
    "auto_start": true
  },
  "buffer": {
    "database_path": "/home/pi/rpi-edge-client/data/buffer.db",
    "max_records": 70000,
    "cleanup_days": 7
  }
}
```

### MQTT Configuration (`config/mqtt.json`)

```json
{
  "broker": {
    "host": "mqtt.vibrasense.io",
    "port": 8883,
    "use_tls": true
  },
  "credentials": {
    "username": "machine_001",
    "password": "YOUR_SECRET_TOKEN"
  }
}
```

### Sensors Configuration (`config/sensors.json`)

```json
{
  "machine_id": 1,
  "sensors": [
    {
      "sensor_id": 1,
      "name": "Vibrazioni Mandrino",
      "type": "vibration",
      "driver": "adxl345",
      "config": {
        "address": "0x53",
        "range": 16,
        "sampling_rate": 1600
      }
    }
  ]
}
```

---

## 🔧 Remote Commands

Send commands via MQTT to topic:
```
vibrasense/{company_id}/machine/{machine_id}/commands
```

### Start Acquisition
```json
{
  "command": "start",
  "timestamp": "2026-03-04T10:00:00Z"
}
```

### Stop Acquisition
```json
{
  "command": "stop",
  "timestamp": "2026-03-04T10:00:00Z"
}
```

### Update Software
```json
{
  "command": "update_software",
  "branch": "main",
  "backup": true,
  "restart": true,
  "rollback_on_fail": true
}
```

### Update Configuration
```json
{
  "command": "update_config",
  "config": {
    "read_interval": 300
  }
}
```

### Reboot Device
```json
{
  "command": "reboot",
  "delay_seconds": 60
}
```

### Get Status
```json
{
  "command": "get_status"
}
```

Responses are published to:
```
vibrasense/{company_id}/machine/{machine_id}/responses
```

---

## 🧪 Testing

### Test without hardware:
```bash
# Run component tests (mock mode)
python3 tests/test_components.py
```

### Test with real hardware:
```bash
# Test I2C devices
sudo i2cdetect -y 1

# Test sensors manually
python3 -c "
from drivers.adxl345 import ADXL345Driver
sensor = ADXL345Driver(1, {'address': '0x53', 'bus': 1})
sensor.initialize()
print(sensor.read_raw())
"
```

---

## 📊 Monitoring

### Service Status
```bash
sudo systemctl status vibrasense-edge
```

### Logs
```bash
# Systemd journal
sudo journalctl -u vibrasense-edge -f

# Application log
tail -f /home/pi/rpi-edge-client/logs/vibrasense.log

# Last 100 lines with errors
sudo journalctl -u vibrasense-edge -n 100 --priority=err
```

### Buffer Statistics
```bash
sqlite3 /home/pi/rpi-edge-client/data/buffer.db "
SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN transmitted=0 THEN 1 ELSE 0 END) as pending,
  SUM(CASE WHEN transmitted=1 THEN 1 ELSE 0 END) as sent
FROM readings_buffer;
"
```

---

## 🔄 Updates

### Manual Update
```bash
cd /home/pi/rpi-edge-client
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart vibrasense-edge
```

### Remote Update
Send MQTT command `update_software` (see Remote Commands section)

### Rollback
```bash
cd /home/pi/rpi-edge-client
git log --oneline -10  # Find commit
git checkout <commit-hash>
sudo systemctl restart vibrasense-edge
```

---

## 🐛 Troubleshooting

### Service won't start
```bash
# Check logs
sudo journalctl -u vibrasense-edge -n 50

# Check configuration syntax
python3 -c "import json; json.load(open('config/config.json'))"

# Check permissions
ls -la /home/pi/rpi-edge-client/
```

### MQTT connection fails
```bash
# Test broker connectivity
ping mqtt.vibrasense.io

# Test MQTT connection
mosquitto_sub -h test.mosquitto.org -p 8883 \
  --capath /etc/ssl/certs -t test/# -v
```

### Sensors not detected
```bash
# Check I2C
sudo i2cdetect -y 1

# Check SPI
ls -l /dev/spidev*

# Check permissions
groups pi  # Should include: i2c, spi, gpio
```

### High CPU/Memory usage
```bash
# Check process
top -p $(pgrep -f vibrasense)

# Check buffer size
du -h /home/pi/rpi-edge-client/data/buffer.db
```

---

## 📚 Documentation

- [Installation Guide](docs/installation.md)
- [Configuration Guide](docs/configuration.md)
- [Hardware Setup](docs/hardware-setup.md)
- [API Reference](docs/api-reference.md)
- [Troubleshooting](docs/troubleshooting.md)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Authors

**VibraSense Team**
- Website: https://vibrasense.io
- Email: support@vibrasense.io
- GitHub: https://github.com/vibrasense

---

## 🙏 Acknowledgments

- Raspberry Pi Foundation for excellent hardware
- Eclipse Paho MQTT for reliable MQTT client
- SciPy/NumPy communities for signal processing tools
- Open source community

---

## 🗺️ Roadmap

### v1.0 (Current - MVP)
- ✅ 3 sensor types support
- ✅ MQTT communication with TLS
- ✅ SQLite buffering
- ✅ Remote commands
- ✅ Auto-recovery watchdog
- ✅ Remote software updates

### v1.1 (Next Release)
- 🔄 FFT spectral analysis
- 🔄 Edge anomaly detection
- 🔄 Local web UI for debugging
- 🔄 OTA firmware updates

### v2.0 (Future)
- 🔄 10+ sensors per machine
- 🔄 Edge ML inference (TensorFlow Lite)
- 🔄 CAN bus / Modbus RTU support
- 🔄 Multi-machine gateway mode

---

## 📞 Support

For support, please:

1. Check [Troubleshooting Guide](docs/troubleshooting.md)
2. Search [GitHub Issues](https://github.com/vibrasense/rpi-edge-client/issues)
3. Create a new issue with:
   - Raspberry Pi model and OS version
   - Error logs (`sudo journalctl -u vibrasense-edge -n 100`)
   - Configuration files (remove sensitive data)

---

**Made with ❤️ for Industry 4.0**
