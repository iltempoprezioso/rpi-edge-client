"""
Watchdog - Monitors system health and performs auto-recovery.
"""
import logging
import subprocess
import time
import socket
from typing import Optional
from datetime import datetime
import threading


class Watchdog:
    """System watchdog for monitoring and auto-recovery."""
    
    def __init__(self, mqtt_client, sensor_manager, config: dict):
        """
        Initialize watchdog.
        
        Args:
            mqtt_client: MQTT client instance
            sensor_manager: Sensor manager instance
            config: Watchdog configuration
        """
        self.logger = logging.getLogger(__name__)
        self.mqtt = mqtt_client
        self.sensors = sensor_manager
        self.config = config
        
        self.enabled = config.get('enabled', True)
        self.heartbeat_interval = config.get('heartbeat_interval', 60)
        self.network_check_interval = config.get('network_check_interval', 300)
        self.auto_recovery = config.get('auto_recovery', True)
        
        self.is_running = False
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.network_thread: Optional[threading.Thread] = None
        
        self.mqtt_fail_count = 0
        self.network_fail_count = 0
        
        self.logger.info(f"Watchdog initialized (enabled={self.enabled})")
    
    def start(self):
        """Start watchdog monitoring."""
        if not self.enabled:
            self.logger.info("Watchdog disabled, not starting")
            return
        
        self.is_running = True
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="WatchdogHeartbeat"
        )
        self.heartbeat_thread.start()
        
        # Start network check thread
        self.network_thread = threading.Thread(
            target=self._network_check_loop,
            daemon=True,
            name="WatchdogNetwork"
        )
        self.network_thread.start()
        
        self.logger.info("Watchdog started")
    
    def stop(self):
        """Stop watchdog monitoring."""
        self.is_running = False
        
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        
        if self.network_thread:
            self.network_thread.join(timeout=5)
        
        self.logger.info("Watchdog stopped")
    
    def _heartbeat_loop(self):
        """Send periodic heartbeat messages."""
        while self.is_running:
            try:
                heartbeat_data = self._get_heartbeat_data()
                
                if self.mqtt.is_connected:
                    if self.mqtt.publish_heartbeat(heartbeat_data):
                        self.mqtt_fail_count = 0
                        self.logger.debug("Heartbeat sent")
                    else:
                        self.mqtt_fail_count += 1
                        self.logger.warning(f"Heartbeat failed ({self.mqtt_fail_count})")
                else:
                    self.mqtt_fail_count += 1
                    self.logger.warning(f"MQTT disconnected ({self.mqtt_fail_count})")
                
                # Auto-recovery if too many failures
                if self.auto_recovery and self.mqtt_fail_count >= 10:
                    self.logger.error("Too many MQTT failures, attempting recovery")
                    self._recover_mqtt()
                
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(self.heartbeat_interval)
    
    def _network_check_loop(self):
        """Periodically check network connectivity."""
        while self.is_running:
            try:
                # Check internet connectivity
                if self._check_network():
                    self.network_fail_count = 0
                    self.logger.debug("Network check OK")
                else:
                    self.network_fail_count += 1
                    self.logger.warning(f"Network check failed ({self.network_fail_count})")
                
                # Auto-recovery if too many failures
                if self.auto_recovery and self.network_fail_count >= 3:
                    self.logger.error("Network connectivity lost, attempting recovery")
                    self._recover_network()
                
                time.sleep(self.network_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in network check loop: {e}")
                time.sleep(self.network_check_interval)
    
    def _get_heartbeat_data(self) -> dict:
        """Generate heartbeat data."""
        try:
            # CPU temperature
            cpu_temp = None
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    cpu_temp = float(f.read()) / 1000.0
            except:
                pass
            
            # Uptime
            uptime = None
            try:
                with open('/proc/uptime', 'r') as f:
                    uptime = int(float(f.readline().split()[0]))
            except:
                pass
            
            # Sensor status
            sensor_status = self.sensors.get_sensor_status()
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'device_id': f"rpi-{self.sensors.machine_id}",
                'machine_id': self.sensors.machine_id,
                'company_id': self.sensors.company_id,
                'status': 'online',
                'uptime_seconds': uptime,
                'cpu_temp_celsius': round(cpu_temp, 1) if cpu_temp else None,
                'mqtt_connected': self.mqtt.is_connected,
                'sensors_healthy': sensor_status.get('healthy_sensors', 0),
                'sensors_total': sensor_status.get('total_sensors', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating heartbeat data: {e}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    def _check_network(self, host: str = "8.8.8.8", port: int = 53, timeout: int = 5) -> bool:
        """
        Check network connectivity by trying to connect to a known host.
        
        Args:
            host: Host to connect to (default: Google DNS)
            port: Port to connect to
            timeout: Connection timeout in seconds
            
        Returns:
            True if network is reachable
        """
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except Exception:
            return False
    
    def _recover_mqtt(self):
        """Attempt to recover MQTT connection."""
        try:
            self.logger.info("Attempting MQTT recovery...")
            
            # Disconnect and reconnect
            self.mqtt.disconnect()
            time.sleep(5)
            
            if self.mqtt.connect():
                self.mqtt_fail_count = 0
                self.logger.info("✓ MQTT recovered successfully")
                
                # Send recovery notification
                status_data = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'event': 'mqtt_recovered',
                    'message': 'MQTT connection restored after failure'
                }
                self.mqtt.publish_status(status_data)
            else:
                self.logger.error("MQTT recovery failed")
                
        except Exception as e:
            self.logger.error(f"Error during MQTT recovery: {e}")
    
    def _recover_network(self):
        """Attempt to recover network connectivity."""
        try:
            self.logger.info("Attempting network recovery...")
            
            # Try to restart network interface
            result = subprocess.run(
                ['sudo', 'ip', 'link', 'set', 'eth0', 'down'],
                capture_output=True,
                timeout=10
            )
            
            time.sleep(2)
            
            result = subprocess.run(
                ['sudo', 'ip', 'link', 'set', 'eth0', 'up'],
                capture_output=True,
                timeout=10
            )
            
            time.sleep(5)
            
            # Check if recovered
            if self._check_network():
                self.network_fail_count = 0
                self.logger.info("✓ Network recovered successfully")
                
                # Reconnect MQTT
                if not self.mqtt.is_connected:
                    self._recover_mqtt()
            else:
                self.logger.error("Network recovery failed")
                
        except Exception as e:
            self.logger.error(f"Error during network recovery: {e}")
    
    def get_watchdog_status(self) -> dict:
        """Get watchdog status information."""
        return {
            'enabled': self.enabled,
            'is_running': self.is_running,
            'mqtt_fail_count': self.mqtt_fail_count,
            'network_fail_count': self.network_fail_count,
            'mqtt_connected': self.mqtt.is_connected if self.mqtt else False,
            'last_heartbeat': datetime.utcnow().isoformat()
        }
