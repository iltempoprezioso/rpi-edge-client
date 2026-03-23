# VibraSense Edge Client - Deployment Checklist

## ✅ Pre-Deployment Checklist

### Hardware Preparation
- [ ] Raspberry Pi 4/5 with adequate power supply (5V 3A)
- [ ] microSD card 32GB+ (Class 10, UHS-I)
- [ ] Sensors connected:
  - [ ] ADXL345 on I2C (address 0x53)
  - [ ] MAX31855 on SPI (CS pin 8)
  - [ ] ACS712 via MCP3008 ADC (channel 0)
- [ ] Network connection (Ethernet recommended for production)
- [ ] Proper grounding and EMI protection

### Software Installation
- [ ] Raspberry Pi OS Lite (64-bit) flashed
- [ ] SSH enabled and accessible
- [ ] System updated (`sudo apt update && sudo apt upgrade`)
- [ ] Repository cloned to `/home/pi/rpi-edge-client`
- [ ] Installation script executed successfully
- [ ] Virtual environment created and dependencies installed
- [ ] I2C and SPI interfaces enabled
- [ ] User added to i2c, spi, gpio groups

### Configuration
- [ ] `config/config.json` edited with correct:
  - [ ] device_id
  - [ ] machine_id
  - [ ] company_id
  - [ ] read_interval
- [ ] `config/mqtt.json` configured with:
  - [ ] broker host
  - [ ] port (8883 for TLS)
  - [ ] credentials (username/password)
  - [ ] TLS certificates (if using mutual TLS)
- [ ] `config/sensors.json` configured with:
  - [ ] Correct sensor addresses
  - [ ] Appropriate sampling rates
  - [ ] Threshold values set

### Testing
- [ ] Component tests pass (`python3 tests/test_components.py`)
- [ ] I2C devices detected (`sudo i2cdetect -y 1`)
- [ ] SPI devices accessible (`ls -l /dev/spidev*`)
- [ ] MQTT broker reachable (`ping mqtt.vibrasense.io`)
- [ ] Test sensor readings manually
- [ ] Buffer database created (`ls -l data/buffer.db`)

### Service Setup
- [ ] Systemd service file copied to `/etc/systemd/system/`
- [ ] Systemd daemon reloaded
- [ ] Service enabled for auto-start
- [ ] Service started successfully
- [ ] Service status shows "active (running)"
- [ ] No errors in journal logs

### Monitoring Setup
- [ ] Log rotation configured
- [ ] Monitoring dashboard access verified
- [ ] Alert thresholds configured
- [ ] Backup strategy defined

---

## 🚀 Deployment Steps

### Step 1: Hardware Setup (30 minutes)
```bash
# Connect sensors to Raspberry Pi
# Verify connections with multimeter
# Check power supply voltage
```

### Step 2: Software Installation (15 minutes)
```bash
cd /home/pi
git clone https://github.com/vibrasense/rpi-edge-client.git
cd rpi-edge-client
chmod +x scripts/install.sh
./scripts/install.sh
```

### Step 3: Configuration (10 minutes)
```bash
nano config/config.json
nano config/mqtt.json
nano config/sensors.json
```

### Step 4: Testing (10 minutes)
```bash
source venv/bin/activate
python3 tests/test_components.py
sudo i2cdetect -y 1
```

### Step 5: Service Start (5 minutes)
```bash
sudo systemctl start vibrasense-edge
sudo systemctl status vibrasense-edge
sudo journalctl -u vibrasense-edge -f
```

**Total Deployment Time: ~70 minutes**

---

## 🔍 Post-Deployment Verification

### Immediate Checks (First 5 minutes)
- [ ] Service is running without errors
- [ ] MQTT connection established
- [ ] First sensor readings transmitted
- [ ] No critical errors in logs
- [ ] CPU temperature < 70°C
- [ ] Memory usage < 50%

### Short-term Monitoring (First Hour)
- [ ] Regular heartbeats every 60s
- [ ] Sensor readings every 10 minutes
- [ ] Buffer filling correctly
- [ ] No sensor failures
- [ ] Network connectivity stable
- [ ] MQTT reconnections (if any) successful

### Long-term Monitoring (First 24 Hours)
- [ ] Data continuity verified
- [ ] Buffer cleanup working
- [ ] No memory leaks
- [ ] CPU usage stable
- [ ] Disk usage acceptable
- [ ] Remote commands working

---

## 📊 Health Metrics

### System Metrics
| Metric | Target | Critical |
|--------|--------|----------|
| CPU Usage | <15% | >80% |
| Memory Usage | <40% | >80% |
| CPU Temperature | <60°C | >75°C |
| Disk Usage | <50% | >90% |
| Network Errors | 0/hour | >10/hour |

### Application Metrics
| Metric | Target | Critical |
|--------|--------|----------|
| MQTT Connection | 100% | <95% |
| Sensor Read Success | >99% | <95% |
| Buffer Transmit Rate | >95% | <80% |
| Heartbeat Frequency | 1/min | <1/5min |
| Command Response Time | <5s | >30s |

---

## 🐛 Troubleshooting Common Issues

### Service won't start
```bash
# Check logs
sudo journalctl -u vibrasense-edge -n 100 --no-pager

# Check configuration
python3 -c "import json; json.load(open('config/config.json'))"

# Check permissions
ls -la /home/pi/rpi-edge-client/
sudo chown -R pi:pi /home/pi/rpi-edge-client/
```

### MQTT connection fails
```bash
# Test connectivity
ping mqtt.vibrasense.io

# Test MQTT port
nc -zv mqtt.vibrasense.io 8883

# Check credentials in config/mqtt.json
# Verify TLS certificates (if using mutual TLS)
```

### Sensors not detected
```bash
# Scan I2C
sudo i2cdetect -y 1

# Check SPI
ls -l /dev/spidev*

# Verify GPIO permissions
groups pi  # Should include i2c, spi, gpio

# Reboot if interfaces just enabled
sudo reboot
```

### High CPU usage
```bash
# Check process
top -p $(pgrep -f vibrasense)

# Reduce sampling rate in config/sensors.json
# Increase read_interval in config/config.json
```

### Buffer filling up
```bash
# Check buffer size
du -h data/buffer.db

# Check untransmitted records
sqlite3 data/buffer.db "SELECT COUNT(*) FROM readings_buffer WHERE transmitted=0"

# Check MQTT connection
sudo journalctl -u vibrasense-edge | grep "MQTT"
```

---

## 🔄 Remote Update Procedure

### Update via MQTT Command
```json
{
  "command": "update_software",
  "branch": "main",
  "backup": true,
  "restart": true,
  "rollback_on_fail": true
}
```

### Manual Update
```bash
cd /home/pi/rpi-edge-client
git fetch origin
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart vibrasense-edge
```

### Rollback Procedure
```bash
cd /home/pi/rpi-edge-client
git log --oneline -10
git checkout <previous-commit>
sudo systemctl restart vibrasense-edge
```

---

## 📞 Emergency Contacts

- **Technical Support**: support@vibrasense.io
- **On-Call Engineer**: [phone number]
- **Documentation**: https://github.com/vibrasense/rpi-edge-client
- **MQTT Broker Status**: https://status.vibrasense.io

---

## 📝 Deployment Log Template

```
Deployment Date: _______________
Site Location: _________________
Machine ID: ____________________
Raspberry Pi SN: _______________
Deployed By: ___________________

Pre-Deployment Checks:
- Hardware: [ ] Pass [ ] Fail
- Network: [ ] Pass [ ] Fail
- Configuration: [ ] Pass [ ] Fail
- Testing: [ ] Pass [ ] Fail

Deployment:
- Installation Time: ________ minutes
- Configuration Time: ________ minutes
- Testing Time: ________ minutes
- Total Time: ________ minutes

Post-Deployment:
- Service Status: [ ] Running [ ] Issues
- MQTT Connected: [ ] Yes [ ] No
- First Reading: ________ (timestamp)
- Sensor Status: ________

Notes:
_________________________________
_________________________________
_________________________________

Signature: _____________________
Date: __________________________
```

---

**Last Updated**: 2026-03-04  
**Version**: 1.0.0
