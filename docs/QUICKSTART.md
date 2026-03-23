# Quick Start Guide - VibraSense Edge Client

## Hardware Requirements

- Raspberry Pi 4 Model B (2GB+ RAM) or Raspberry Pi 5
- microSD card 32GB+ (Class 10, UHS-I recommended)
- Power supply 5V 3A (official Raspberry Pi adapter)
- Industrial sensors (ADXL345, MAX31855, ACS712)
- Internet connection (Ethernet or WiFi)

## Software Requirements

- Raspberry Pi OS Lite (64-bit, Debian 12 Bookworm)
- Python 3.11+
- Git

## Installation Steps

### 1. Flash Raspberry Pi OS

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/):

1. Choose OS: **Raspberry Pi OS Lite (64-bit)**
2. Configure settings:
   - Set hostname: `vibrasense-rpi-001`
   - Enable SSH with password authentication
   - Set username: `pi`, password: (your choice)
   - Configure WiFi (if needed)
   - Set locale and timezone

3. Flash to microSD card

### 2. Initial Boot

```bash
# SSH into Raspberry Pi
ssh pi@vibrasense-rpi-001.local

# Update system
sudo apt update && sudo apt upgrade -y
```

### 3. Clone Repository

```bash
cd /home/pi
git clone https://github.com/vibrasense/rpi-edge-client.git
cd rpi-edge-client
```

### 4. Run Installation Script

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

The script will:
- Install system packages
- Enable I2C and SPI interfaces
- Create Python virtual environment
- Install dependencies
- Create configuration files
- Install systemd service

### 5. Configure Device

Edit configuration files:

```bash
# Main configuration
nano config/config.json
# Set: machine_id, company_id, device_id

# MQTT configuration
nano config/mqtt.json
# Set: broker host, credentials

# Sensors configuration
nano config/sensors.json
# Configure your sensors
```

### 6. Test Sensors (Optional)

```bash
# Activate virtual environment
source venv/bin/activate

# Run component tests (mock mode)
python3 tests/test_components.py

# Test I2C devices
sudo i2cdetect -y 1
```

### 7. Start Service

```bash
# Start service
sudo systemctl start vibrasense-edge

# Check status
sudo systemctl status vibrasense-edge

# View logs
sudo journalctl -u vibrasense-edge -f
```

### 8. Reboot (If needed)

If I2C/SPI were just enabled:

```bash
sudo reboot
```

## Verification

### Check Service Status

```bash
sudo systemctl status vibrasense-edge
```

Expected output:
```
● vibrasense-edge.service - VibraSense Edge Client
   Loaded: loaded (/etc/systemd/system/vibrasense-edge.service; enabled)
   Active: active (running) since...
```

### View Live Logs

```bash
# Systemd journal
sudo journalctl -u vibrasense-edge -f

# Application log
tail -f /home/pi/rpi-edge-client/logs/vibrasense.log
```

### Check MQTT Connection

In logs, look for:
```
✓ Connected to MQTT broker (rc=0)
Subscribed to vibrasense/1/machine/1/commands
```

### Check Sensor Readings

In logs, look for:
```
✓ Readings transmitted (3 sensors)
```

## Common Issues

### Service won't start

```bash
# Check logs
sudo journalctl -u vibrasense-edge -n 50

# Check configuration syntax
python3 -c "import json; json.load(open('config/config.json'))"

# Check file permissions
ls -la /home/pi/rpi-edge-client/
```

### I2C devices not detected

```bash
# Scan I2C bus
sudo i2cdetect -y 1

# Check if I2C enabled
lsmod | grep i2c

# Add user to i2c group (then logout/login)
sudo usermod -a -G i2c,spi,gpio pi
```

### MQTT connection fails

```bash
# Test internet connectivity
ping -c 3 8.8.8.8

# Test broker connectivity
ping mqtt.vibrasense.io

# Check firewall (if any)
sudo iptables -L
```

## Next Steps

1. **Monitor System:**
   - Set up log monitoring
   - Check buffer statistics
   - Monitor CPU temperature

2. **Configure Alerts:**
   - Set threshold values in `config/sensors.json`
   - Configure alert notifications

3. **Test Remote Commands:**
   - Use MQTT client to send test commands
   - Verify command responses

4. **Production Deployment:**
   - Set up multiple devices
   - Configure automatic backups
   - Set up monitoring dashboard

## Support

For help:
- Check [Full Documentation](README.md)
- Review [Troubleshooting Guide](docs/troubleshooting.md)
- Open [GitHub Issue](https://github.com/vibrasense/rpi-edge-client/issues)
- Contact: support@vibrasense.io

---

**Installation time: ~15-20 minutes**
**Difficulty: Intermediate**
