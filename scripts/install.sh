#!/bin/bash
###############################################################################
# VibraSense Edge Client - Installation Script
# For Raspberry Pi 4/5 with Raspberry Pi OS Lite (64-bit)
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installation paths
INSTALL_DIR="/home/pi/rpi-edge-client"
SERVICE_NAME="vibrasense-edge"
SERVICE_FILE="${SERVICE_NAME}.service"

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -eq 0 ]; then
        print_error "Please do not run this script as root"
        exit 1
    fi
}

check_raspberry_pi() {
    if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
        print_warn "This doesn't appear to be a Raspberry Pi"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

install_system_packages() {
    print_info "Installing system packages..."
    
    sudo apt update
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        git \
        sqlite3 \
        i2c-tools \
        python3-dev \
        build-essential \
        hostapd \
        dnsmasq \
        wireless-tools
    
    print_info "✓ System packages installed"
}

enable_hardware_interfaces() {
    print_info "Enabling hardware interfaces (I2C, SPI)..."
    
    # Enable I2C
    if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
        echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt > /dev/null
        print_info "I2C enabled (reboot required)"
    else
        print_info "I2C already enabled"
    fi
    
    # Enable SPI
    if ! grep -q "^dtparam=spi=on" /boot/config.txt; then
        echo "dtparam=spi=on" | sudo tee -a /boot/config.txt > /dev/null
        print_info "SPI enabled (reboot required)"
    else
        print_info "SPI already enabled"
    fi
    
    # Add user to i2c and spi groups
    sudo usermod -a -G i2c,spi,gpio "$USER"
    
    print_info "✓ Hardware interfaces configured"
}

setup_project() {
    print_info "Setting up project directory..."
    
    cd "$INSTALL_DIR"
    
    # Create required directories
    mkdir -p data logs backups config
    
    # Create Python virtual environment
    if [ ! -d "venv" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate venv and install dependencies
    source venv/bin/activate
    print_info "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    print_info "✓ Project setup complete"
}

configure_settings() {
    print_info "Configuring settings..."
    
    # Copy example configs if not exist
    if [ ! -f "config/config.json" ]; then
        cp config/config.example.json config/config.json
        print_warn "Created config/config.json from example - PLEASE EDIT IT"
    fi
    
    if [ ! -f "config/mqtt.json" ]; then
        cp config/mqtt.example.json config/mqtt.json
        print_warn "Created config/mqtt.json from example - PLEASE EDIT IT"
    fi
    
    if [ ! -f "config/sensors.json" ]; then
        cp config/sensors.example.json config/sensors.json
        print_warn "Created config/sensors.json from example - PLEASE EDIT IT"
    fi
    
    print_info "✓ Configuration files ready"
}

test_sensors() {
    print_info "Testing sensor connectivity..."
    
    # Test I2C
    print_info "Scanning I2C bus..."
    if command -v i2cdetect &> /dev/null; then
        sudo i2cdetect -y 1 || true
    fi
    
    print_info "✓ Sensor test complete"
}

install_systemd_service() {
    print_info "Installing systemd services..."
    
    # Copy edge client service
    sudo cp "$INSTALL_DIR/$SERVICE_FILE" /etc/systemd/system/
    
    # Copy WiFi setup service
    sudo cp "$INSTALL_DIR/vibrasense-wifi-setup.service" /etc/systemd/system/
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable services
    sudo systemctl enable "$SERVICE_NAME"
    sudo systemctl enable vibrasense-wifi-setup
    
    print_info "✓ Systemd services installed and enabled"
}

setup_captive_portal_option() {
    echo ""
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_info "📱 WiFi Captive Portal Setup (Optional)"
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Do you want to enable WiFi Captive Portal?"
    echo ""
    echo "This allows first-time WiFi configuration via smartphone"
    echo "without monitor/keyboard (plug-and-play experience)."
    echo ""
    echo "Features:"
    echo "  ✓ Smartphone-based WiFi setup"
    echo "  ✓ No monitor/keyboard needed"
    echo "  ✓ Auto-fallback to hotspot if WiFi lost"
    echo "  ✓ Custom VibraSense branding"
    echo ""
    echo "Note: Requires internet connection for installation"
    echo ""
    read -p "Enable captive portal? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Setting up captive portal..."
        
        if [ -f "$INSTALL_DIR/scripts/setup_captive_portal.sh" ]; then
            bash "$INSTALL_DIR/scripts/setup_captive_portal.sh"
        else
            print_error "Captive portal script not found"
        fi
    else
        print_info "Skipping captive portal setup"
        echo "You can run it later with:"
        echo "  sudo $INSTALL_DIR/scripts/setup_captive_portal.sh"
    fi
}

print_instructions() {
    echo ""
    echo "=========================================="
    echo "  VibraSense Edge Client Installation"
    echo "=========================================="
    echo ""
    print_info "Installation completed successfully!"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Edit configuration files:"
    echo "   nano $INSTALL_DIR/config/config.json"
    echo "   nano $INSTALL_DIR/config/mqtt.json"
    echo "   nano $INSTALL_DIR/config/sensors.json"
    echo ""
    echo "2. (Optional) Setup WiFi Captive Portal:"
    echo "   sudo $INSTALL_DIR/scripts/setup_captive_portal.sh"
    echo ""
    echo "3. Start the service:"
    echo "   sudo systemctl start $SERVICE_NAME"
    echo ""
    echo "4. Check service status:"
    echo "   sudo systemctl status $SERVICE_NAME"
    echo ""
    echo "5. View logs:"
    echo "   sudo journalctl -u $SERVICE_NAME -f"
    echo "   tail -f $INSTALL_DIR/logs/vibrasense.log"
    echo ""
    echo "6. If I2C/SPI were just enabled, reboot:"
    echo "   sudo reboot"
    echo ""
    echo "=========================================="
}

# Main installation flow
main() {
    echo ""
    echo "=========================================="
    echo "  VibraSense Edge Client Installer"
    echo "=========================================="
    echo ""
    
    check_root
    check_raspberry_pi
    
    print_info "Installing to: $INSTALL_DIR"
    
    # Installation steps
    install_system_packages
    enable_hardware_interfaces
    setup_project
    configure_settings
    test_sensors
    install_systemd_service
    
    # Optional: Captive portal setup
    setup_captive_portal_option
    
    print_instructions
}

# Run installation
main
