"""
Command Handler - Processes remote commands from MQTT.
"""
import logging
import subprocess
import time
import os
from typing import Dict, Any, Callable, Optional
from datetime import datetime


class CommandHandler:
    """Handles remote commands received via MQTT."""
    
    def __init__(self, mqtt_client, config: Dict[str, Any]):
        """
        Initialize command handler.
        
        Args:
            mqtt_client: MQTT client instance
            config: Main configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.mqtt = mqtt_client
        self.config = config
        
        # Callbacks for different operations
        self.start_callback: Optional[Callable] = None
        self.stop_callback: Optional[Callable] = None
        self.update_config_callback: Optional[Callable] = None
        
        # Set MQTT message callback
        self.mqtt.set_message_callback(self.handle_message)
        
        self.logger.info("Command handler initialized")
    
    def set_start_callback(self, callback: Callable):
        """Set callback for START command."""
        self.start_callback = callback
    
    def set_stop_callback(self, callback: Callable):
        """Set callback for STOP command."""
        self.stop_callback = callback
    
    def set_update_config_callback(self, callback: Callable[[Dict], None]):
        """Set callback for UPDATE_CONFIG command."""
        self.update_config_callback = callback
    
    def handle_message(self, topic: str, message: Dict[str, Any]):
        """
        Handle incoming MQTT message.
        
        Args:
            topic: MQTT topic
            message: Message payload as dictionary
        """
        try:
            command = message.get('command')
            
            if not command:
                self.logger.warning("Message without command field")
                return
            
            self.logger.info(f"Received command: {command}")
            
            # Route to appropriate handler
            if command == 'start':
                self._handle_start(message)
            elif command == 'stop':
                self._handle_stop(message)
            elif command == 'update_config':
                self._handle_update_config(message)
            elif command == 'update_software':
                self._handle_update_software(message)
            elif command == 'rollback_software':
                self._handle_rollback_software(message)
            elif command == 'reboot':
                self._handle_reboot(message)
            elif command == 'get_status':
                self._handle_get_status(message)
            else:
                self.logger.warning(f"Unknown command: {command}")
                self._send_response('error', f"Unknown command: {command}")
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            self._send_response('error', str(e))
    
    def _handle_start(self, message: Dict[str, Any]):
        """Handle START command."""
        try:
            if self.start_callback:
                self.start_callback()
                self._send_response('success', 'Acquisition started')
            else:
                self._send_response('error', 'Start callback not set')
        except Exception as e:
            self._send_response('error', f"Start failed: {e}")
    
    def _handle_stop(self, message: Dict[str, Any]):
        """Handle STOP command."""
        try:
            if self.stop_callback:
                self.stop_callback()
                self._send_response('success', 'Acquisition stopped')
            else:
                self._send_response('error', 'Stop callback not set')
        except Exception as e:
            self._send_response('error', f"Stop failed: {e}")
    
    def _handle_update_config(self, message: Dict[str, Any]):
        """Handle UPDATE_CONFIG command."""
        try:
            new_config = message.get('config', {})
            
            if not new_config:
                self._send_response('error', 'No configuration provided')
                return
            
            if self.update_config_callback:
                self.update_config_callback(new_config)
                self._send_response('success', f'Configuration updated: {list(new_config.keys())}')
            else:
                self._send_response('error', 'Update config callback not set')
                
        except Exception as e:
            self._send_response('error', f"Config update failed: {e}")
    
    def _handle_update_software(self, message: Dict[str, Any]):
        """Handle UPDATE_SOFTWARE command."""
        try:
            branch = message.get('branch', 'main')
            backup = message.get('backup', True)
            restart = message.get('restart', True)
            rollback_on_fail = message.get('rollback_on_fail', True)
            
            self.logger.info(f"Starting software update from branch: {branch}")
            
            # Import update manager
            from .update_manager import UpdateManager
            
            update_config = self.config.get('update', {})
            update_manager = UpdateManager(
                repo_path=update_config.get('git_repository', '/home/pi/rpi-edge-client'),
                backup_enabled=backup
            )
            
            # Perform update
            success, message_text = update_manager.update_software(
                branch=branch,
                test_after_update=True,
                rollback_on_fail=rollback_on_fail
            )
            
            if success:
                self._send_response('success', f'Software updated: {message_text}')
                
                if restart:
                    self.logger.info("Restarting service after update...")
                    time.sleep(2)
                    subprocess.run(['sudo', 'systemctl', 'restart', 'vibrasense-edge'])
            else:
                self._send_response('error', f'Update failed: {message_text}')
                
        except Exception as e:
            self.logger.error(f"Software update error: {e}")
            self._send_response('error', f"Software update failed: {e}")
    
    def _handle_rollback_software(self, message: Dict[str, Any]):
        """Handle ROLLBACK_SOFTWARE command."""
        try:
            target_commit = message.get('target_commit', 'previous')
            
            self.logger.info(f"Rolling back software to: {target_commit}")
            
            from .update_manager import UpdateManager
            
            update_config = self.config.get('update', {})
            update_manager = UpdateManager(
                repo_path=update_config.get('git_repository', '/home/pi/rpi-edge-client')
            )
            
            success, message_text = update_manager.rollback(target_commit)
            
            if success:
                self._send_response('success', f'Rollback successful: {message_text}')
                
                # Restart service
                time.sleep(2)
                subprocess.run(['sudo', 'systemctl', 'restart', 'vibrasense-edge'])
            else:
                self._send_response('error', f'Rollback failed: {message_text}')
                
        except Exception as e:
            self.logger.error(f"Rollback error: {e}")
            self._send_response('error', f"Rollback failed: {e}")
    
    def _handle_reboot(self, message: Dict[str, Any]):
        """Handle REBOOT command."""
        try:
            delay_seconds = message.get('delay_seconds', 60)
            
            self.logger.warning(f"System reboot scheduled in {delay_seconds} seconds")
            self._send_response('success', f'Reboot scheduled in {delay_seconds} seconds')
            
            # Schedule reboot
            time.sleep(min(delay_seconds, 5))  # Send response first
            
            subprocess.run(['sudo', 'shutdown', '-r', f'+{delay_seconds // 60}'])
            
        except Exception as e:
            self.logger.error(f"Reboot error: {e}")
            self._send_response('error', f"Reboot failed: {e}")
    
    def _handle_get_status(self, message: Dict[str, Any]):
        """Handle GET_STATUS command."""
        try:
            # Get system info
            status = self._get_system_status()
            self._send_response('success', 'Status retrieved', data=status)
            
        except Exception as e:
            self.logger.error(f"Get status error: {e}")
            self._send_response('error', f"Failed to get status: {e}")
    
    def _get_system_status(self) -> Dict[str, Any]:
        """Get system status information."""
        try:
            # Uptime
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
            
            # CPU temperature
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    cpu_temp = float(f.read()) / 1000.0
            except:
                cpu_temp = None
            
            # Memory info
            mem_info = {}
            try:
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if 'MemTotal' in line:
                            mem_info['total'] = int(line.split()[1])
                        elif 'MemAvailable' in line:
                            mem_info['available'] = int(line.split()[1])
            except:
                pass
            
            # Git info
            git_info = {}
            try:
                result = subprocess.run(
                    ['git', 'rev-parse', '--short', 'HEAD'],
                    cwd=self.config.get('update', {}).get('git_repository', '.'),
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    git_info['commit'] = result.stdout.strip()
                
                result = subprocess.run(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    cwd=self.config.get('update', {}).get('git_repository', '.'),
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    git_info['branch'] = result.stdout.strip()
            except:
                pass
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'uptime_seconds': int(uptime_seconds),
                'cpu_temp_celsius': round(cpu_temp, 1) if cpu_temp else None,
                'memory_mb': {
                    'total': round(mem_info.get('total', 0) / 1024, 0),
                    'available': round(mem_info.get('available', 0) / 1024, 0)
                } if mem_info else None,
                'software': git_info
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {}
    
    def _send_response(self, status: str, message: str, data: Optional[Dict] = None):
        """
        Send command response via MQTT.
        
        Args:
            status: 'success' or 'error'
            message: Response message
            data: Optional additional data
        """
        try:
            response = {
                'timestamp': datetime.utcnow().isoformat(),
                'status': status,
                'message': message
            }
            
            if data:
                response['data'] = data
            
            self.mqtt.publish_response(response)
            
        except Exception as e:
            self.logger.error(f"Error sending response: {e}")
