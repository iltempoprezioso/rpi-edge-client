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
CONFIG_FILE = "/home/iltempoprezioso/rpi-edge-client/config/wifi.json"
SETUP_FLAG = "/home/iltempoprezioso/rpi-edge-client/.wifi_configured"

import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('wifi_setup')

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
    """Gestisce la configurazione WiFi tramite hotspot, usando NetworkManager (nmcli).

    Differenze rispetto alla versione precedente:
      - NON esegue piu' 'systemctl stop NetworkManager' (causava l'isolamento del Pi)
      - NON usa hostapd / dnsmasq / wpa_supplicant / dhcpcd (dhcpcd non esiste su questo sistema)
      - eth0 continua a funzionare normalmente durante la configurazione del WiFi
    """

    HOTSPOT_CON = 'vibrasense-setup'

    def __init__(self):
        self.config_file = Path(CONFIG_FILE)
        self.setup_flag = Path(SETUP_FLAG)

    def _nmcli(self, args, timeout=45):
        """Esegue nmcli e restituisce (ok, output)."""
        try:
            r = subprocess.run(['sudo', 'nmcli'] + args,
                               capture_output=True, text=True, timeout=timeout)
            return r.returncode == 0, (r.stdout or '') + (r.stderr or '')
        except Exception as e:
            return False, str(e)

    def is_wifi_configured(self) -> bool:
        """True se il WiFi e' gia' configurato e connesso."""
        return self.setup_flag.exists() and self.has_wifi_connection()

    def has_wifi_connection(self) -> bool:
        """True se wlan0 e' connessa a una rete vera (non all'hotspot di setup)."""
        ok, out = self._nmcli(['-t', '-f', 'DEVICE,STATE,CONNECTION', 'device', 'status'], timeout=10)
        if not ok:
            return False
        for line in out.splitlines():
            p = line.split(':')
            if len(p) >= 3 and p[0] == 'wlan0':
                return p[1] == 'connected' and p[2] != self.HOTSPOT_CON
        return False

    def create_hotspot(self) -> bool:
        """Alza l'hotspot di configurazione su wlan0. Non tocca NetworkManager ne' eth0."""
        try:
            self._nmcli(['connection', 'down', self.HOTSPOT_CON], timeout=10)
            self._nmcli(['connection', 'delete', self.HOTSPOT_CON], timeout=10)
            ok, out = self._nmcli(['device', 'wifi', 'hotspot', 'ifname', 'wlan0',
                                   'con-name', self.HOTSPOT_CON, 'ssid', HOTSPOT_SSID,
                                   'password', HOTSPOT_PASSWORD])
            if not ok:
                logger.error("Hotspot non avviato: %s" % out)
                return False
            self._nmcli(['connection', 'modify', self.HOTSPOT_CON,
                         'ipv4.addresses', '192.168.4.1/24'], timeout=10)
            self._nmcli(['connection', 'up', self.HOTSPOT_CON], timeout=20)
            logger.info("Hotspot attivo: SSID=%s - http://192.168.4.1:5000" % HOTSPOT_SSID)
            return True
        except Exception as e:
            logger.error("Errore creazione hotspot: %s" % e)
            return False

    def stop_hotspot(self) -> bool:
        """Spegne e rimuove l'hotspot di setup."""
        self._nmcli(['connection', 'down', self.HOTSPOT_CON], timeout=10)
        self._nmcli(['connection', 'delete', self.HOTSPOT_CON], timeout=10)
        return True

    def scan_networks(self) -> list:
        """Elenca le reti WiFi visibili, ordinate per potenza di segnale."""
        networks = []
        try:
            self._nmcli(['device', 'wifi', 'rescan'], timeout=20)
            ok, out = self._nmcli(['-t', '-f', 'SSID,SIGNAL,SECURITY', 'device', 'wifi', 'list'], timeout=20)
            if not ok:
                return []
            seen = set()
            for line in out.splitlines():
                p = line.split(':')
                if len(p) < 2 or not p[0].strip():
                    continue
                ssid = p[0].strip()
                if ssid in seen:
                    continue
                seen.add(ssid)
                try:
                    sig = int(p[1])
                except (ValueError, IndexError):
                    sig = 0
                networks.append({'ssid': ssid, 'signal': sig,
                                 'security': p[2] if len(p) > 2 and p[2] else 'Open'})
            networks.sort(key=lambda n: n['signal'], reverse=True)
        except Exception as e:
            logger.error("Errore scansione reti: %s" % e)
        return networks

    def configure_wifi(self, ssid: str, password: str, country: str = 'IT') -> bool:
        """Connette wlan0 alla rete indicata. Se fallisce, riattiva l'hotspot."""
        try:
            self.stop_hotspot()
            time.sleep(2)
            ok, out = self._nmcli(['device', 'wifi', 'connect', ssid,
                                   'password', password, 'ifname', 'wlan0'], timeout=60)
            if not ok:
                logger.error("Connessione a %s fallita: %s" % (ssid, out))
                self.create_hotspot()
                return False
            time.sleep(3)
            if not self.has_wifi_connection():
                logger.error("Connessione a %s non risulta attiva" % ssid)
                self.create_hotspot()
                return False
            self.setup_flag.parent.mkdir(parents=True, exist_ok=True)
            self.setup_flag.touch()
            logger.info("Connesso a %s" % ssid)
            return True
        except Exception as e:
            logger.error("Errore configurazione WiFi: %s" % e)
            self.create_hotspot()
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
