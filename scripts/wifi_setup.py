#!/usr/bin/env python3
"""
WiFi Setup Manager - Hotspot-based WiFi configuration
Allows mobile device to configure WiFi on first boot.
"""
import subprocess
import os
import time
import json
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify

# Configuration
HOTSPOT_SSID = "VibraSense-Setup"
HOTSPOT_PASSWORD = "vibrasense2026"
CONFIG_FILE = "/home/pi/rpi-edge-client/config/wifi.json"
SETUP_FLAG = "/home/pi/rpi-edge-client/.wifi_configured"

app = Flask(__name__)

# HTML Template for WiFi setup page
SETUP_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>VibraSense WiFi Setup</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
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
            margin-bottom: 10px;
        }
        .logo p {
            color: #666;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 25px;
        }
        label {
            display: block;
            color: #333;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 14px;
        }
        input, select {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
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
        .btn:hover {
            transform: translateY(-2px);
        }
        .btn:active {
            transform: translateY(0);
        }
        .status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            display: none;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            display: block;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            display: block;
        }
        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
        }
        .loading.show {
            display: block;
        }
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .info-box {
            background: #e7f3ff;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 13px;
            color: #004085;
        }
        .scan-btn {
            background: #f0f0f0;
            color: #333;
            padding: 10px;
            margin-bottom: 15px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>🔧 VibraSense</h1>
            <p>WiFi Configuration</p>
        </div>

        <div class="info-box">
            ℹ️ Connect this device to your WiFi network. After configuration, the setup hotspot will be disabled.
        </div>

        <form id="wifiForm">
            <button type="button" class="scan-btn" onclick="scanNetworks()">📡 Scan Networks</button>
            
            <div class="form-group">
                <label for="ssid">Network Name (SSID)</label>
                <input type="text" id="ssid" name="ssid" required 
                       placeholder="Enter WiFi network name" list="networks">
                <datalist id="networks"></datalist>
            </div>

            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required
                       placeholder="Enter WiFi password">
            </div>

            <div class="form-group">
                <label for="country">Country Code</label>
                <select id="country" name="country">
                    <option value="IT">Italy (IT)</option>
                    <option value="US">United States (US)</option>
                    <option value="GB">United Kingdom (GB)</option>
                    <option value="DE">Germany (DE)</option>
                    <option value="FR">France (FR)</option>
                </select>
            </div>

            <button type="submit" class="btn">Connect to WiFi</button>
        </form>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="margin-top: 10px; color: #666;">Connecting...</p>
        </div>

        <div class="status" id="status"></div>
    </div>

    <script>
        async function scanNetworks() {
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = '🔄 Scanning...';
            
            try {
                const response = await fetch('/scan');
                const data = await response.json();
                
                const datalist = document.getElementById('networks');
                datalist.innerHTML = '';
                
                data.networks.forEach(network => {
                    const option = document.createElement('option');
                    option.value = network;
                    datalist.appendChild(option);
                });
                
                btn.textContent = '✅ Networks Found';
                setTimeout(() => {
                    btn.disabled = false;
                    btn.textContent = '📡 Scan Networks';
                }, 2000);
                
            } catch (error) {
                btn.textContent = '❌ Scan Failed';
                setTimeout(() => {
                    btn.disabled = false;
                    btn.textContent = '📡 Scan Networks';
                }, 2000);
            }
        }

        document.getElementById('wifiForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());
            
            document.getElementById('loading').classList.add('show');
            document.getElementById('status').style.display = 'none';
            
            try {
                const response = await fetch('/configure', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                document.getElementById('loading').classList.remove('show');
                
                const statusDiv = document.getElementById('status');
                if (result.success) {
                    statusDiv.className = 'status success';
                    statusDiv.innerHTML = `
                        ✅ <strong>Success!</strong><br>
                        Connecting to ${data.ssid}...<br>
                        <small>This page will close automatically.</small>
                    `;
                    
                    setTimeout(() => {
                        window.location.href = 'about:blank';
                    }, 5000);
                } else {
                    statusDiv.className = 'status error';
                    statusDiv.innerHTML = `
                        ❌ <strong>Connection Failed</strong><br>
                        ${result.error}<br>
                        <small>Please check your credentials and try again.</small>
                    `;
                }
                
            } catch (error) {
                document.getElementById('loading').classList.remove('show');
                const statusDiv = document.getElementById('status');
                statusDiv.className = 'status error';
                statusDiv.innerHTML = `
                    ❌ <strong>Error</strong><br>
                    Failed to connect to the device.
                `;
            }
        });
    </script>
</body>
</html>
"""


class WiFiSetupManager:
    """Manages WiFi configuration via mobile hotspot."""
    
    def __init__(self):
        self.config_file = Path(CONFIG_FILE)
        self.setup_flag = Path(SETUP_FLAG)
    
    def is_wifi_configured(self) -> bool:
        """Check if WiFi is already configured."""
        return self.setup_flag.exists() and self.has_wifi_connection()
    
    def has_wifi_connection(self) -> bool:
        """Check if device has active WiFi connection."""
        try:
            result = subprocess.run(
                ['iwgetid', '-r'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and len(result.stdout.strip()) > 0
        except:
            return False
    
    def create_hotspot(self) -> bool:
        """Create WiFi hotspot for configuration."""
        try:
            print("Creating WiFi hotspot...")
            
            # Stop existing networking
            subprocess.run(['sudo', 'systemctl', 'stop', 'NetworkManager'], check=False)
            
            # Configure hostapd
            hostapd_conf = f"""
interface=wlan0
driver=nl80211
ssid={HOTSPOT_SSID}
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={HOTSPOT_PASSWORD}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
            
            with open('/tmp/hostapd.conf', 'w') as f:
                f.write(hostapd_conf)
            
            # Configure dnsmasq for DHCP
            dnsmasq_conf = """
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
"""
            
            with open('/tmp/dnsmasq.conf', 'w') as f:
                f.write(dnsmasq_conf)
            
            # Configure network interface
            subprocess.run(['sudo', 'ip', 'addr', 'flush', 'dev', 'wlan0'], check=False)
            subprocess.run(['sudo', 'ip', 'addr', 'add', '192.168.4.1/24', 'dev', 'wlan0'])
            subprocess.run(['sudo', 'ip', 'link', 'set', 'wlan0', 'up'])
            
            # Start services
            subprocess.run(['sudo', 'dnsmasq', '-C', '/tmp/dnsmasq.conf'])
            subprocess.run(['sudo', 'hostapd', '/tmp/hostapd.conf', '-B'])
            
            print(f"✓ Hotspot created: {HOTSPOT_SSID}")
            print(f"  Password: {HOTSPOT_PASSWORD}")
            print(f"  IP: 192.168.4.1")
            
            return True
            
        except Exception as e:
            print(f"Error creating hotspot: {e}")
            return False
    
    def scan_networks(self) -> list:
        """Scan for available WiFi networks."""
        try:
            result = subprocess.run(
                ['sudo', 'iwlist', 'wlan0', 'scan'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            networks = []
            for line in result.stdout.split('\n'):
                if 'ESSID:' in line:
                    ssid = line.split('ESSID:"')[1].split('"')[0]
                    if ssid and ssid not in networks:
                        networks.append(ssid)
            
            return sorted(networks)
            
        except Exception as e:
            print(f"Error scanning networks: {e}")
            return []
    
    def configure_wifi(self, ssid: str, password: str, country: str = 'IT') -> bool:
        """Configure WiFi connection."""
        try:
            print(f"Configuring WiFi: {ssid}")
            
            # Save configuration
            config = {
                'ssid': ssid,
                'password': password,
                'country': country,
                'configured_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Create wpa_supplicant configuration
            wpa_conf = f"""
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country={country}

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
"""
            
            with open('/tmp/wpa_supplicant.conf', 'w') as f:
                f.write(wpa_conf)
            
            subprocess.run(['sudo', 'cp', '/tmp/wpa_supplicant.conf', 
                          '/etc/wpa_supplicant/wpa_supplicant.conf'])
            
            # Stop hotspot
            subprocess.run(['sudo', 'pkill', 'hostapd'], check=False)
            subprocess.run(['sudo', 'pkill', 'dnsmasq'], check=False)
            
            # Restart networking
            subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'])
            subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'], check=False)
            
            # Wait for connection
            time.sleep(5)
            
            # Check if connected
            if self.has_wifi_connection():
                # Mark as configured
                self.setup_flag.touch()
                print("✓ WiFi configured successfully")
                return True
            else:
                print("✗ Failed to connect to WiFi")
                return False
                
        except Exception as e:
            print(f"Error configuring WiFi: {e}")
            return False


# Flask routes
manager = WiFiSetupManager()

@app.route('/')
def index():
    """Main setup page."""
    return render_template_string(SETUP_PAGE)

@app.route('/scan')
def scan():
    """Scan for WiFi networks."""
    networks = manager.scan_networks()
    return jsonify({'networks': networks})

@app.route('/configure', methods=['POST'])
def configure():
    """Configure WiFi from form submission."""
    data = request.get_json()
    
    ssid = data.get('ssid', '').strip()
    password = data.get('password', '').strip()
    country = data.get('country', 'IT')
    
    if not ssid or not password:
        return jsonify({
            'success': False,
            'error': 'SSID and password are required'
        })
    
    if len(password) < 8:
        return jsonify({
            'success': False,
            'error': 'Password must be at least 8 characters'
        })
    
    success = manager.configure_wifi(ssid, password, country)
    
    if success:
        return jsonify({
            'success': True,
            'message': f'Connected to {ssid}'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to connect. Check credentials.'
        })


def main():
    """Main entry point."""
    print("=" * 50)
    print("VibraSense WiFi Setup Manager")
    print("=" * 50)
    
    # Check if already configured
    if manager.is_wifi_configured():
        print("✓ WiFi already configured")
        print("  Run with --reset to reconfigure")
        return
    
    print("WiFi not configured. Starting setup mode...")
    
    # Create hotspot
    if manager.create_hotspot():
        print("\n" + "=" * 50)
        print("Setup Instructions:")
        print("=" * 50)
        print(f"1. Connect your phone to WiFi: {HOTSPOT_SSID}")
        print(f"2. Password: {HOTSPOT_PASSWORD}")
        print("3. Open browser and go to: http://192.168.4.1:5000")
        print("4. Enter your WiFi credentials")
        print("=" * 50)
        print("\nStarting web server on http://192.168.4.1:5000")
        
        # Start web server
        app.run(host='192.168.4.1', port=5000, debug=False)
    else:
        print("✗ Failed to create hotspot")
        return 1


if __name__ == '__main__':
    import sys
    
    if '--reset' in sys.argv:
        # Reset configuration
        Path(SETUP_FLAG).unlink(missing_ok=True)
        Path(CONFIG_FILE).unlink(missing_ok=True)
        print("✓ Configuration reset")
    else:
        main()
