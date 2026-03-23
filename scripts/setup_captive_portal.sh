#!/bin/bash
###############################################################################
# VibraSense Edge Client - WiFi Captive Portal Setup
# 
# Installs and configures RaspAP for plug-and-play WiFi configuration.
# Enables first-time setup via smartphone without monitor/keyboard.
#
# Usage: sudo ./setup_captive_portal.sh
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/home/pi/rpi-edge-client"
RASPAP_WEBROOT="/var/www/html"
DEFAULT_PASSWORD="vibrasense2026"

print_header() {
    echo ""
    echo -e "${BLUE}=================================================${NC}"
    echo -e "${BLUE}  VibraSense - WiFi Captive Portal Setup${NC}"
    echo -e "${BLUE}=================================================${NC}"
    echo ""
}

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
    if [ "$EUID" -ne 0 ]; then
        print_error "Please run as root: sudo $0"
        exit 1
    fi
}

check_internet() {
    print_info "Checking internet connection..."
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        print_error "No internet connection. Please connect to internet first."
        exit 1
    fi
    print_info "✓ Internet connection OK"
}

install_dependencies() {
    print_info "Installing system dependencies..."
    
    apt-get update
    apt-get install -y \
        hostapd \
        dnsmasq \
        iptables-persistent \
        lighttpd \
        php-cgi \
        git \
        dhcpcd5
    
    print_info "✓ Dependencies installed"
}

install_raspap() {
    print_info "Installing RaspAP..."
    print_warn "This will take 5-10 minutes..."
    
    # Download and install RaspAP
    # Using non-interactive mode
    wget -q https://install.raspap.com -O /tmp/raspap_install.sh
    
    # Run installer with auto-yes and defaults
    bash /tmp/raspap_install.sh --yes --openvpn 0 --adblock 0 --wireguard 0
    
    print_info "✓ RaspAP installed"
}

configure_custom_ssid() {
    print_info "Configuring custom SSID..."
    
    # Get device/machine ID from config or hostname
    DEVICE_ID=$(hostname)
    MACHINE_ID="001"
    
    # Try to get machine_id from config file
    if [ -f "$INSTALL_DIR/config/config.json" ]; then
        MACHINE_ID=$(grep -oP '"machine_id":\s*\K\d+' "$INSTALL_DIR/config/config.json" || echo "001")
    fi
    
    SSID="VibraSense-Setup-${MACHINE_ID}"
    
    # Update hostapd configuration
    sed -i "s/^ssid=.*/ssid=${SSID}/" /etc/hostapd/hostapd.conf
    sed -i "s/^wpa_passphrase=.*/wpa_passphrase=${DEFAULT_PASSWORD}/" /etc/hostapd/hostapd.conf
    
    # Set country code to IT
    sed -i "s/^country_code=.*/country_code=IT/" /etc/hostapd/hostapd.conf
    
    print_info "✓ SSID configured: ${SSID}"
    print_info "✓ Default password: ${DEFAULT_PASSWORD}"
}

configure_dhcp() {
    print_info "Configuring DHCP server..."
    
    # Set DHCP range for captive portal
    cat > /etc/dnsmasq.d/090_raspap.conf << 'EOF'
# RaspAP hostapd configuration
interface=wlan0
bind-dynamic
domain-needed
bogus-priv
dhcp-range=10.3.141.50,10.3.141.150,255.255.255.0,12h
dhcp-option=3,10.3.141.1
dhcp-option=6,10.3.141.1
address=/#/10.3.141.1
EOF
    
    print_info "✓ DHCP configured"
}

create_custom_portal_page() {
    print_info "Creating custom captive portal page..."
    
    # Create custom landing page
    cat > "$RASPAP_WEBROOT/portal.php" << 'EOF'
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VibraSense - Configurazione WiFi</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 400px;
            width: 100%;
            padding: 40px 30px;
        }
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo h1 {
            color: #667eea;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .logo p {
            color: #666;
            font-size: 14px;
        }
        .icon {
            font-size: 48px;
            margin-bottom: 10px;
        }
        .info-box {
            background: #f0f4ff;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin-bottom: 25px;
            border-radius: 5px;
        }
        .info-box p {
            color: #444;
            font-size: 14px;
            line-height: 1.6;
        }
        .btn-primary {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
        }
        .btn-primary:active {
            transform: translateY(0);
        }
        .footer {
            text-align: center;
            margin-top: 25px;
            padding-top: 25px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <div class="icon">📡</div>
            <h1>VibraSense</h1>
            <p>Sistema di Monitoraggio Industriale</p>
        </div>
        
        <div class="info-box">
            <p><strong>👋 Benvenuto!</strong><br>
            Per iniziare, configura la connessione WiFi del dispositivo alla rete della tua officina.</p>
        </div>
        
        <button class="btn-primary" onclick="window.location.href='/'">
            Configura WiFi →
        </button>
        
        <div class="footer">
            <p>VibraSense Edge Client v1.0<br>
            Support: support@vibrasense.io</p>
        </div>
    </div>
</body>
</html>
EOF
    
    # Set captive portal to use custom page
    if [ -f "/etc/lighttpd/conf-available/50-raspap-router.conf" ]; then
        sed -i 's|"/var/www/html"|"/var/www/html/portal.php"|g' /etc/lighttpd/conf-available/50-raspap-router.conf
    fi
    
    print_info "✓ Custom portal page created"
}

configure_autostart() {
    print_info "Configuring auto-start hotspot..."
    
    # Enable RaspAP service on boot
    systemctl enable raspapd
    systemctl enable hostapd
    systemctl enable dnsmasq
    
    print_info "✓ Auto-start configured"
}

configure_fallback() {
    print_info "Configuring WiFi fallback to hotspot..."
    
    # Create fallback script
    cat > /usr/local/bin/vibrasense-wifi-fallback.sh << 'EOF'
#!/bin/bash
###############################################################################
# VibraSense WiFi Fallback
# Automatically starts hotspot if WiFi client connection is lost
###############################################################################

TIMEOUT=300  # 5 minutes
LOGFILE="/var/log/vibrasense-wifi-fallback.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOGFILE"
}

# Check if connected to WiFi as client
if iwgetid -r > /dev/null 2>&1; then
    SSID=$(iwgetid -r)
    log "Connected to WiFi: $SSID"
    
    # Check if we can ping gateway
    if ping -c 1 -W 5 $(ip route | grep default | awk '{print $3}') > /dev/null 2>&1; then
        log "Network connectivity OK"
        exit 0
    else
        log "WARNING: Connected to WiFi but no network connectivity"
    fi
else
    log "NOT connected to WiFi"
fi

# Check how long we've been disconnected
if [ -f /tmp/wifi_disconnected_since ]; then
    DISCONNECT_TIME=$(cat /tmp/wifi_disconnected_since)
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - DISCONNECT_TIME))
    
    if [ $ELAPSED -gt $TIMEOUT ]; then
        log "Disconnected for ${ELAPSED}s (>${TIMEOUT}s), starting hotspot..."
        
        # Start hotspot mode
        systemctl start hostapd
        systemctl start dnsmasq
        
        log "Hotspot started"
        
        # Remove disconnect marker
        rm -f /tmp/wifi_disconnected_since
    else
        log "Disconnected for ${ELAPSED}s, waiting..."
    fi
else
    # First time detecting disconnection
    date +%s > /tmp/wifi_disconnected_since
    log "Disconnect detected, starting timer..."
fi
EOF
    
    chmod +x /usr/local/bin/vibrasense-wifi-fallback.sh
    
    # Add cron job (check every 2 minutes)
    (crontab -l 2>/dev/null | grep -v vibrasense-wifi-fallback; echo "*/2 * * * * /usr/local/bin/vibrasense-wifi-fallback.sh") | crontab -
    
    print_info "✓ WiFi fallback configured (checks every 2 minutes)"
}

create_qr_code_info() {
    print_info "Creating QR code information file..."
    
    # Get SSID and password
    SSID=$(grep "^ssid=" /etc/hostapd/hostapd.conf | cut -d'=' -f2)
    
    # Create WiFi QR code content
    # Format: WIFI:S:<SSID>;T:WPA;P:<PASSWORD>;;
    QR_CONTENT="WIFI:S:${SSID};T:WPA;P:${DEFAULT_PASSWORD};;"
    
    cat > "$INSTALL_DIR/docs/WIFI_SETUP_INFO.txt" << EOF
==============================================
  VibraSense - WiFi Setup Information
==============================================

HOTSPOT CREDENTIALS:
--------------------
SSID:     ${SSID}
Password: ${DEFAULT_PASSWORD}

SETUP INSTRUCTIONS:
------------------
1. Power on the Raspberry Pi
2. Wait 60 seconds for boot
3. On your smartphone, go to WiFi settings
4. Connect to: ${SSID}
5. Enter password: ${DEFAULT_PASSWORD}
6. Browser will open automatically
7. Enter your office WiFi credentials
8. Device will connect and start working

WEB INTERFACE:
--------------
URL: http://10.3.141.1
Admin login: admin / secret

QR CODE (for WiFi connection):
------------------------------
${QR_CONTENT}

SUPPORT:
--------
Email: support@vibrasense.io
Docs: https://github.com/vibrasense/rpi-edge-client

==============================================
EOF
    
    print_info "✓ WiFi info file created: docs/WIFI_SETUP_INFO.txt"
    
    # Try to generate QR code image if qrencode is available
    if command -v qrencode &> /dev/null; then
        qrencode -o "$INSTALL_DIR/docs/wifi_qr_code.png" "$QR_CONTENT"
        print_info "✓ QR code image generated: docs/wifi_qr_code.png"
    else
        print_warn "Install 'qrencode' to generate QR code image: sudo apt install qrencode"
    fi
}

print_completion_info() {
    SSID=$(grep "^ssid=" /etc/hostapd/hostapd.conf | cut -d'=' -f2)
    
    echo ""
    echo -e "${GREEN}=================================================${NC}"
    echo -e "${GREEN}  ✅ WiFi Captive Portal Setup Complete!${NC}"
    echo -e "${GREEN}=================================================${NC}"
    echo ""
    echo -e "${BLUE}Hotspot Configuration:${NC}"
    echo -e "  SSID:     ${SSID}"
    echo -e "  Password: ${DEFAULT_PASSWORD}"
    echo ""
    echo -e "${BLUE}Web Interface:${NC}"
    echo -e "  URL:   http://10.3.141.1"
    echo -e "  Login: admin / secret"
    echo ""
    echo -e "${BLUE}Features Enabled:${NC}"
    echo -e "  ✓ Captive portal for first-time setup"
    echo -e "  ✓ Auto-fallback to hotspot if WiFi lost"
    echo -e "  ✓ Custom VibraSense branding"
    echo -e "  ✓ Smartphone-friendly interface"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo -e "  1. Reboot the Raspberry Pi: ${BLUE}sudo reboot${NC}"
    echo -e "  2. Connect smartphone to: ${SSID}"
    echo -e "  3. Configure your office WiFi"
    echo -e "  4. Device will connect automatically"
    echo ""
    echo -e "${BLUE}WiFi setup info saved to:${NC}"
    echo -e "  $INSTALL_DIR/docs/WIFI_SETUP_INFO.txt"
    echo ""
    echo -e "${GREEN}=================================================${NC}"
}

# Main installation flow
main() {
    print_header
    
    check_root
    check_internet
    
    print_info "Starting captive portal installation..."
    
    install_dependencies
    install_raspap
    configure_custom_ssid
    configure_dhcp
    create_custom_portal_page
    configure_autostart
    configure_fallback
    create_qr_code_info
    
    print_completion_info
    
    # Ask for reboot
    echo -n "Reboot now to activate captive portal? (y/N): "
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_info "Rebooting in 3 seconds..."
        sleep 3
        reboot
    else
        print_info "Remember to reboot manually: sudo reboot"
    fi
}

# Run installation
main
