# Changelog

All notable changes to VibraSense Edge Client will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-03-15

### Added - WiFi Captive Portal 📱

#### WiFi Setup Features
- **Captive Portal**: Smartphone-based WiFi configuration (RaspAP-based)
  - Automatic hotspot creation on first boot
  - Custom SSID: `VibraSense-Setup-{machine_id}`
  - WPA2 password: `vibrasense2026` (customizable)
  - Custom branded landing page
  - Web UI at http://10.3.141.1

- **Auto-fallback mechanism**: 
  - Monitors WiFi connection every 2 minutes
  - Automatically returns to hotspot mode if connection lost >5 minutes
  - Cron-based fallback script
  - Logging to `/var/log/vibrasense-wifi-fallback.log`

- **Installation script**: `scripts/setup_captive_portal.sh`
  - One-command installation
  - Automatic configuration
  - QR code generation for easy smartphone connection
  - WiFi info file generation

- **User documentation**: `docs/WIFI_SETUP_GUIDE.md`
  - Step-by-step smartphone setup guide
  - Troubleshooting section
  - LED status indicators
  - Support information

#### Current Monitoring Enhancements
- **Advanced current analysis** in DataProcessor:
  - Crest factor calculation (signal quality indicator)
  - Coefficient of variation (stability metric)
  - Estimated power calculation (V × I × PF)
  - Anomaly detection with baseline comparison
  - Deviation percentage tracking

- **Documentation**: `docs/CURRENT_SENSORS_GUIDE.md`
  - Complete guide for current/power monitoring
  - Sensor recommendations (ACS712, PZEM-004T, SCT-013, INA226)
  - Pattern diagnostics and use cases
  - ML-ready algorithms (drift detection, MCSA)
  - ROI analysis

### Changed
- Updated `install.sh` to optionally setup captive portal
- Enhanced `data_processor.py` with advanced current metrics
- Updated README with captive portal instructions

### Security
- WPA2 encryption for hotspot
- Configurable default password
- Admin credentials for RaspAP web UI

---

## [1.0.0] - 2026-03-04

### Added - MVP Release 🚀

#### Core Features
- **Sensor Manager**: Multi-sensor orchestration system
  - Support for ADXL345 (vibration), MAX31855 (temperature), ACS712 (current)
  - I2C, SPI, and ADC interfaces
  - Mock mode for development without hardware
  - Auto-recovery for sensor failures
  - Health monitoring and error tracking

- **MQTT Client**: Robust cloud communication
  - MQTT v3.1.1 with TLS 1.2+ encryption
  - QoS 0/1 support for different message types
  - Topic structure: readings, status, heartbeat, commands, responses
  - Automatic reconnection and retry logic
  - Test.mosquitto.org support for development

- **Buffer Manager**: Local data persistence
  - SQLite database for up to 70,000 readings (~7 days)
  - Automatic retry of failed transmissions
  - Cleanup of old records
  - Buffer statistics and monitoring

- **Data Processor**: Advanced signal processing
  - Digital filters: high-pass (1Hz), low-pass (500Hz), notch (50Hz)
  - RMS (Root Mean Square) calculation
  - Peak-to-peak and peak detection
  - Threshold monitoring with warning/critical levels
  - FFT spectrum analysis (ready for v1.1)

- **Command Handler**: Remote device management
  - START/STOP acquisition commands
  - Configuration updates via MQTT
  - Software updates with Git pull
  - System reboot scheduling
  - Status query and reporting

- **Update Manager**: Safe software updates
  - Automatic backup before updates
  - Git-based update mechanism
  - Smoke tests after updates
  - Automatic rollback on failure
  - Backup retention (last 5 backups)

- **Watchdog**: System health monitoring
  - Heartbeat messages every 60 seconds
  - Network connectivity checks every 5 minutes
  - Automatic MQTT recovery
  - Network interface restart on failure
  - CPU temperature and uptime monitoring

#### Drivers
- **ADXL345 Driver**: 3-axis accelerometer
  - I2C interface support
  - Configurable range (±2g to ±16g)
  - Sampling rates up to 1600 Hz
  - Multi-sample reading for signal processing

- **MAX31855 Driver**: K-type thermocouple
  - SPI interface support
  - Temperature range: -200°C to +1350°C
  - 0.25°C resolution
  - Internal temperature monitoring
  - Error detection (open circuit, shorts)

- **ACS712 Driver**: Hall effect current sensor
  - ADC interface via MCP3008
  - Range: 0-30A (configurable)
  - RMS current calculation
  - Voltage output monitoring

#### Installation & Deployment
- Automated installation script for Raspberry Pi
- Systemd service with auto-restart
- Hardware interface configuration (I2C, SPI)
- Python virtual environment setup
- Configuration file templates

#### Testing
- Component test suite
- Mock hardware support
- Sensor connectivity tests
- MQTT configuration validation
- Buffer operations verification

#### Documentation
- Comprehensive README with features and usage
- Quick start installation guide
- Configuration examples
- Troubleshooting guide
- API documentation structure

#### Configuration
- JSON-based configuration system
- Main configuration (device, acquisition, buffer)
- MQTT configuration (broker, TLS, topics)
- Sensors configuration (per-sensor settings)
- Environment-based configuration support

### Security
- TLS/SSL encryption for MQTT
- Certificate-based authentication support
- Secure credential storage
- No hardcoded secrets

### Performance
- Efficient sensor reading cycles (configurable intervals)
- Minimal CPU usage (~5-10% on Raspberry Pi 4)
- Low memory footprint (~100MB RAM)
- Optimized SQLite queries

## [Unreleased]

### Planned for v1.1
- FFT spectral analysis implementation
- Edge anomaly detection (basic)
- Local web UI for debugging
- OTA firmware updates
- Enhanced logging with rotation

### Planned for v2.0
- Support for 10+ sensors per machine
- Edge ML inference (TensorFlow Lite)
- CAN bus / Modbus RTU support
- Multi-machine gateway mode
- Advanced predictive algorithms

---

## Version History

- **v1.0.0** (2026-03-04): Initial MVP release
  - 3,375 lines of Python code
  - 25 project files
  - 6 configuration templates
  - Full documentation
  - Tested on Raspberry Pi 4 Model B

---

## Contributors

**VibraSense Team**
- Software Architecture
- Driver Development
- Signal Processing
- System Integration
- Documentation

---

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.
