"""
VibraSense Edge Client - Main Application
Raspberry Pi edge software for industrial sensor monitoring.
"""
import sys
import signal
import logging
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sensor_manager import SensorManager
from src.mqtt_client import MQTTClient
from src.buffer_manager import BufferManager
from src.data_processor import DataProcessor
from src.command_handler import CommandHandler
from src.watchdog import Watchdog


class VibraSenseEdgeClient:
    """Main application class for VibraSense edge client."""
    
    def __init__(self, config_dir: str = '/home/pi/rpi-edge-client/config'):
        """
        Initialize edge client.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        
        # Setup logging first
        self._setup_logging()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("=" * 60)
        self.logger.info("VibraSense Edge Client Starting...")
        self.logger.info("=" * 60)
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize components
        self.sensor_manager: Optional[SensorManager] = None
        self.mqtt_client: Optional[MQTTClient] = None
        self.buffer_manager: Optional[BufferManager] = None
        self.data_processor: Optional[DataProcessor] = None
        self.command_handler: Optional[CommandHandler] = None
        self.watchdog: Optional[Watchdog] = None
        
        self.is_running = False
        self.acquisition_enabled = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self):
        """Setup logging configuration."""
        # Create logs directory
        log_dir = Path('/home/pi/rpi-edge-client/logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'vibrasense.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def _load_config(self) -> dict:
        """Load main configuration."""
        config_file = self.config_dir / 'config.json'
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            self.logger.info(f"Configuration loaded from {config_file}")
            return config
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {config_file}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            sys.exit(1)
    
    def initialize(self) -> bool:
        """
        Initialize all components.
        
        Returns:
            True if initialization successful
        """
        try:
            self.logger.info("Initializing components...")
            
            # 1. Initialize sensor manager
            sensors_config = self.config_dir / 'sensors.json'
            self.sensor_manager = SensorManager(str(sensors_config))
            
            if not self.sensor_manager.initialize_all_sensors():
                self.logger.error("Sensor initialization failed")
                return False
            
            # 2. Initialize buffer manager
            buffer_config = self.config.get('buffer', {})
            self.buffer_manager = BufferManager(
                db_path=buffer_config.get('database_path', 'data/buffer.db'),
                max_records=buffer_config.get('max_records', 70000),
                cleanup_days=buffer_config.get('cleanup_days', 7)
            )
            
            # 3. Initialize data processor
            self.data_processor = DataProcessor(sampling_rate=1600)
            
            # 4. Initialize MQTT client
            mqtt_config = self.config_dir / 'mqtt.json'
            device_config = self.config.get('device', {})
            self.mqtt_client = MQTTClient(
                config_path=str(mqtt_config),
                machine_id=device_config.get('machine_id', 1),
                company_id=device_config.get('company_id', 1)
            )
            
            if not self.mqtt_client.connect():
                self.logger.warning("MQTT connection failed, will retry in background")
            
            # 5. Initialize command handler
            self.command_handler = CommandHandler(self.mqtt_client, self.config)
            self.command_handler.set_start_callback(self.start_acquisition)
            self.command_handler.set_stop_callback(self.stop_acquisition)
            self.command_handler.set_update_config_callback(self.update_configuration)
            
            # 6. Initialize watchdog
            watchdog_config = self.config.get('watchdog', {})
            self.watchdog = Watchdog(
                mqtt_client=self.mqtt_client,
                sensor_manager=self.sensor_manager,
                config=watchdog_config
            )
            
            self.logger.info("✓ All components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization error: {e}", exc_info=True)
            return False
    
    def start(self):
        """Start the edge client."""
        try:
            if not self.initialize():
                self.logger.error("Initialization failed, exiting")
                sys.exit(1)
            
            self.is_running = True
            
            # Start watchdog
            self.watchdog.start()
            
            # Send initial status
            self._send_status('started')
            
            # Check if acquisition is enabled
            acquisition_config = self.config.get('acquisition', {})
            self.acquisition_enabled = acquisition_config.get('enabled', True)
            
            if self.acquisition_enabled:
                self.logger.info("Starting data acquisition...")
                self._acquisition_loop()
            else:
                self.logger.info("Data acquisition disabled, waiting for commands...")
                self._idle_loop()
                
        except Exception as e:
            self.logger.error(f"Error starting edge client: {e}", exc_info=True)
            self.shutdown()
    
    def _acquisition_loop(self):
        """Main acquisition loop."""
        read_interval = self.sensor_manager.get_read_interval()
        self.logger.info(f"Acquisition loop started (interval: {read_interval}s)")
        
        while self.is_running and self.acquisition_enabled:
            try:
                cycle_start = time.time()
                
                # Read all sensors
                readings = self.sensor_manager.read_all_sensors()
                
                if readings:
                    # Save to buffer
                    self.buffer_manager.save_reading(readings)
                    
                    # Try to transmit via MQTT
                    if self.mqtt_client.is_connected:
                        if self.mqtt_client.publish_readings(readings):
                            self.logger.info(f"✓ Readings transmitted ({len(readings['readings'])} sensors)")
                        else:
                            self.logger.warning("MQTT transmission failed, buffered locally")
                    else:
                        self.logger.warning("MQTT disconnected, buffered locally")
                    
                    # Retry untransmitted readings
                    self._retry_buffered_readings()
                
                # Cleanup old records
                self.buffer_manager.cleanup_old_records()
                
                # Calculate sleep time
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, read_interval - cycle_duration)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                self.logger.error(f"Error in acquisition loop: {e}", exc_info=True)
                time.sleep(read_interval)
    
    def _idle_loop(self):
        """Idle loop when acquisition is disabled."""
        while self.is_running and not self.acquisition_enabled:
            time.sleep(1)
    
    def _retry_buffered_readings(self):
        """Retry transmitting buffered readings."""
        try:
            if not self.mqtt_client.is_connected:
                return
            
            # Get untransmitted readings
            buffered = self.buffer_manager.get_untransmitted_readings(limit=50)
            
            if not buffered:
                return
            
            self.logger.info(f"Retrying {len(buffered)} buffered readings...")
            
            # Group by timestamp and machine
            grouped = {}
            for reading in buffered:
                key = (reading['timestamp'], reading['machine_id'])
                if key not in grouped:
                    grouped[key] = {
                        'timestamp': reading['timestamp'],
                        'machine_id': reading['machine_id'],
                        'company_id': reading['company_id'],
                        'readings': []
                    }
                grouped[key]['readings'].append(reading)
            
            # Transmit grouped readings
            transmitted_ids = []
            for data in grouped.values():
                if self.mqtt_client.publish_readings(data):
                    transmitted_ids.extend([r['id'] for r in data['readings']])
            
            # Mark as transmitted
            if transmitted_ids:
                self.buffer_manager.mark_transmitted(transmitted_ids)
                self.logger.info(f"✓ Retransmitted {len(transmitted_ids)} buffered readings")
                
        except Exception as e:
            self.logger.error(f"Error retrying buffered readings: {e}")
    
    def start_acquisition(self):
        """Start data acquisition (command callback)."""
        if self.acquisition_enabled:
            self.logger.info("Acquisition already running")
            return
        
        self.logger.info("Starting acquisition by command...")
        self.acquisition_enabled = True
        self._send_status('acquisition_started')
        self._acquisition_loop()
    
    def stop_acquisition(self):
        """Stop data acquisition (command callback)."""
        if not self.acquisition_enabled:
            self.logger.info("Acquisition already stopped")
            return
        
        self.logger.info("Stopping acquisition by command...")
        self.acquisition_enabled = False
        self._send_status('acquisition_stopped')
    
    def update_configuration(self, new_config: dict):
        """Update configuration (command callback)."""
        try:
            self.logger.info(f"Updating configuration: {list(new_config.keys())}")
            
            # Update in-memory config
            for key, value in new_config.items():
                if key in self.config:
                    self.config[key].update(value)
                else:
                    self.config[key] = value
            
            # Save to file
            config_file = self.config_dir / 'config.json'
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            self.logger.info("Configuration updated successfully")
            self._send_status('config_updated')
            
        except Exception as e:
            self.logger.error(f"Error updating configuration: {e}")
    
    def _send_status(self, event: str):
        """Send status update via MQTT."""
        try:
            status_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'event': event,
                'acquisition_enabled': self.acquisition_enabled,
                'sensors': self.sensor_manager.get_sensor_status(),
                'buffer': self.buffer_manager.get_buffer_stats(),
                'watchdog': self.watchdog.get_watchdog_status()
            }
            
            if self.mqtt_client.is_connected:
                self.mqtt_client.publish_status(status_data)
                
        except Exception as e:
            self.logger.error(f"Error sending status: {e}")
    
    def shutdown(self):
        """Shutdown edge client gracefully."""
        self.logger.info("Shutting down...")
        
        self.is_running = False
        self.acquisition_enabled = False
        
        # Send shutdown status
        self._send_status('shutdown')
        
        # Stop watchdog
        if self.watchdog:
            self.watchdog.stop()
        
        # Close sensors
        if self.sensor_manager:
            self.sensor_manager.close_all_sensors()
        
        # Disconnect MQTT
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        
        self.logger.info("✓ Shutdown complete")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)


def main():
    """Main entry point."""
    # Determine config directory
    if len(sys.argv) > 1:
        config_dir = sys.argv[1]
    else:
        # Try production path, fall back to development path
        if Path('/home/pi/rpi-edge-client/config').exists():
            config_dir = '/home/pi/rpi-edge-client/config'
        else:
            config_dir = str(Path(__file__).parent.parent / 'config')
    
    # Create and start client
    client = VibraSenseEdgeClient(config_dir=config_dir)
    client.start()


if __name__ == '__main__':
    main()
