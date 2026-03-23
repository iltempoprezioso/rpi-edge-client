"""
MQTT Client - Handles communication with MQTT broker.
"""
import json
import logging
import time
import ssl
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import paho.mqtt.client as mqtt


class MQTTClient:
    """MQTT client for VibraSense edge device."""
    
    def __init__(self, config_path: str, machine_id: int, company_id: int):
        """
        Initialize MQTT client.
        
        Args:
            config_path: Path to MQTT configuration file
            machine_id: Machine identifier
            company_id: Company identifier
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path
        self.machine_id = machine_id
        self.company_id = company_id
        
        self.client: Optional[mqtt.Client] = None
        self.is_connected = False
        self.message_callback: Optional[Callable] = None
        
        # Load configuration
        self._load_configuration()
        
        # Initialize client
        self._init_client()
    
    def _load_configuration(self):
        """Load MQTT configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            broker = config.get('broker', {})
            self.host = broker.get('host', 'test.mosquitto.org')
            self.port = broker.get('port', 8883)
            self.use_tls = broker.get('use_tls', True)
            
            credentials = config.get('credentials', {})
            self.username = credentials.get('username')
            self.password = credentials.get('password')
            
            tls = config.get('tls', {})
            self.ca_cert = tls.get('ca_cert')
            self.client_cert = tls.get('client_cert')
            self.client_key = tls.get('client_key')
            self.tls_insecure = tls.get('insecure', False)
            
            topics = config.get('topics', {})
            self.topic_readings = topics.get('readings', 'vibrasense/{company_id}/machine/{machine_id}/readings')
            self.topic_status = topics.get('status', 'vibrasense/{company_id}/machine/{machine_id}/status')
            self.topic_heartbeat = topics.get('heartbeat', 'vibrasense/{company_id}/machine/{machine_id}/heartbeat')
            self.topic_commands = topics.get('commands', 'vibrasense/{company_id}/machine/{machine_id}/commands')
            self.topic_responses = topics.get('responses', 'vibrasense/{company_id}/machine/{machine_id}/responses')
            
            qos = config.get('qos', {})
            self.qos_readings = qos.get('readings', 1)
            self.qos_status = qos.get('status', 1)
            self.qos_heartbeat = qos.get('heartbeat', 0)
            self.qos_commands = qos.get('commands', 1)
            self.qos_responses = qos.get('responses', 1)
            
            retain = config.get('retain', {})
            self.retain_readings = retain.get('readings', False)
            self.retain_status = retain.get('status', True)
            self.retain_heartbeat = retain.get('heartbeat', False)
            
            connection = config.get('connection', {})
            self.keepalive = connection.get('keepalive', 60)
            self.reconnect_delay = connection.get('reconnect_delay', 5)
            
            self.logger.info(f"MQTT configuration loaded: {self.host}:{self.port}")
            
        except FileNotFoundError:
            self.logger.warning(f"MQTT config not found, using defaults")
            self._set_defaults()
        except Exception as e:
            self.logger.error(f"Error loading MQTT config: {e}")
            self._set_defaults()
    
    def _set_defaults(self):
        """Set default MQTT configuration."""
        self.host = 'test.mosquitto.org'
        self.port = 8883
        self.use_tls = True
        self.username = None
        self.password = None
        self.ca_cert = None
        self.client_cert = None
        self.client_key = None
        self.tls_insecure = False
        
        self.topic_readings = 'vibrasense/{company_id}/machine/{machine_id}/readings'
        self.topic_status = 'vibrasense/{company_id}/machine/{machine_id}/status'
        self.topic_heartbeat = 'vibrasense/{company_id}/machine/{machine_id}/heartbeat'
        self.topic_commands = 'vibrasense/{company_id}/machine/{machine_id}/commands'
        self.topic_responses = 'vibrasense/{company_id}/machine/{machine_id}/responses'
        
        self.qos_readings = 1
        self.qos_status = 1
        self.qos_heartbeat = 0
        self.qos_commands = 1
        self.qos_responses = 1
        
        self.retain_readings = False
        self.retain_status = True
        self.retain_heartbeat = False
        
        self.keepalive = 60
        self.reconnect_delay = 5
    
    def _init_client(self):
        """Initialize MQTT client instance."""
        try:
            # Create client with unique ID
            client_id = f"vibrasense_rpi_{self.company_id}_{self.machine_id}"
            self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_publish = self._on_publish
            
            # Set credentials
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            # Configure TLS
            if self.use_tls:
                self._configure_tls()
            
            self.logger.info(f"MQTT client initialized: {client_id}")
            
        except Exception as e:
            self.logger.error(f"Error initializing MQTT client: {e}")
            raise
    
    def _configure_tls(self):
        """Configure TLS/SSL for MQTT."""
        try:
            # Check if certificate files exist
            ca_exists = self.ca_cert and Path(self.ca_cert).exists()
            cert_exists = self.client_cert and Path(self.client_cert).exists()
            key_exists = self.client_key and Path(self.client_key).exists()
            
            if ca_exists and cert_exists and key_exists:
                # Full mutual TLS
                self.client.tls_set(
                    ca_certs=self.ca_cert,
                    certfile=self.client_cert,
                    keyfile=self.client_key,
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLSv1_2
                )
                self.logger.info("TLS configured with client certificates")
            else:
                # Server TLS only (for test.mosquitto.org)
                self.client.tls_set(cert_reqs=ssl.CERT_NONE)
                self.client.tls_insecure_set(True)
                self.logger.info("TLS configured (server only, no client cert)")
                
        except Exception as e:
            self.logger.error(f"Error configuring TLS: {e}")
    
    def connect(self) -> bool:
        """
        Connect to MQTT broker.
        
        Returns:
            True if connection successful
        """
        try:
            self.logger.info(f"Connecting to MQTT broker {self.host}:{self.port}...")
            self.client.connect(self.host, self.port, self.keepalive)
            
            # Start network loop in background
            self.client.loop_start()
            
            # Wait for connection (max 10 seconds)
            for _ in range(20):
                if self.is_connected:
                    return True
                time.sleep(0.5)
            
            self.logger.error("MQTT connection timeout")
            return False
            
        except Exception as e:
            self.logger.error(f"Error connecting to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        try:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
            self.is_connected = False
            self.logger.info("Disconnected from MQTT broker")
        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}")
    
    def publish_readings(self, readings_data: Dict[str, Any]) -> bool:
        """
        Publish sensor readings.
        
        Args:
            readings_data: Dictionary with sensor readings
            
        Returns:
            True if published successfully
        """
        topic = self._format_topic(self.topic_readings)
        payload = json.dumps(readings_data)
        
        return self._publish(topic, payload, self.qos_readings, self.retain_readings)
    
    def publish_status(self, status_data: Dict[str, Any]) -> bool:
        """Publish device status."""
        topic = self._format_topic(self.topic_status)
        payload = json.dumps(status_data)
        
        return self._publish(topic, payload, self.qos_status, self.retain_status)
    
    def publish_heartbeat(self, heartbeat_data: Dict[str, Any]) -> bool:
        """Publish heartbeat."""
        topic = self._format_topic(self.topic_heartbeat)
        payload = json.dumps(heartbeat_data)
        
        return self._publish(topic, payload, self.qos_heartbeat, self.retain_heartbeat)
    
    def publish_response(self, response_data: Dict[str, Any]) -> bool:
        """Publish command response."""
        topic = self._format_topic(self.topic_responses)
        payload = json.dumps(response_data)
        
        return self._publish(topic, payload, self.qos_responses, False)
    
    def _publish(self, topic: str, payload: str, qos: int, retain: bool) -> bool:
        """Internal publish method."""
        try:
            if not self.is_connected:
                self.logger.warning("Not connected to MQTT broker")
                return False
            
            result = self.client.publish(topic, payload, qos=qos, retain=retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.debug(f"Published to {topic}")
                return True
            else:
                self.logger.error(f"Publish failed with code {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error publishing to {topic}: {e}")
            return False
    
    def set_message_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """
        Set callback for incoming messages.
        
        Args:
            callback: Function to call with (topic, message_dict)
        """
        self.message_callback = callback
    
    def _format_topic(self, topic_template: str) -> str:
        """Format topic with company_id and machine_id."""
        return topic_template.format(
            company_id=self.company_id,
            machine_id=self.machine_id
        )
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to broker."""
        if rc == 0:
            self.is_connected = True
            self.logger.info(f"✓ Connected to MQTT broker (rc={rc})")
            
            # Subscribe to commands topic
            commands_topic = self._format_topic(self.topic_commands)
            client.subscribe(commands_topic, qos=self.qos_commands)
            self.logger.info(f"Subscribed to {commands_topic}")
        else:
            self.logger.error(f"Connection failed with code {rc}")
            self.is_connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from broker."""
        self.is_connected = False
        if rc != 0:
            self.logger.warning(f"Unexpected disconnect (rc={rc}), will auto-reconnect")
        else:
            self.logger.info("Disconnected from MQTT broker")
    
    def _on_message(self, client, userdata, msg):
        """Callback when message received."""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            self.logger.info(f"Message received on {topic}")
            
            if self.message_callback:
                self.message_callback(topic, payload)
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    def _on_publish(self, client, userdata, mid):
        """Callback when message published."""
        self.logger.debug(f"Message {mid} published")
