#!/usr/bin/env python3
"""
HTTP Client for VibraSense Cloud Integration
Sends sensor readings to Cloudflare Worker via HTTP POST instead of MQTT
"""

import requests
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class HTTPClient:
    """HTTP client to send sensor data to cloud worker"""
    
    def __init__(self, base_url: str, machine_id: int = 1, company_id: int = 1, device_id: str = "rpi-001"):
        """
        Initialize HTTP client
        
        Args:
            base_url: Base URL of the cloud worker (e.g., https://your-worker.workers.dev)
            machine_id: Machine ID
            company_id: Company ID
            device_id: Unique device identifier
        """
        self.base_url = base_url.rstrip('/')
        self.endpoint = '/api/ingest/readings'
        self.machine_id = machine_id
        self.company_id = company_id
        self.device_id = device_id
        self.timeout = 10  # seconds
        self.is_connected = False
        
        logger.info(f"HTTP Client initialized: {self.base_url}{self.endpoint}")
    
    def connect(self) -> bool:
        """
        Test connection to cloud worker
        
        Returns:
            True if connection successful
        """
        try:
            # Test health endpoint
            health_url = f"{self.base_url}/api/ingest/health"
            response = requests.get(health_url, timeout=5)
            
            if response.status_code == 200:
                logger.info(f"✓ Connected to cloud worker: {self.base_url}")
                self.is_connected = True
                return True
            else:
                logger.error(f"Health check failed: HTTP {response.status_code}")
                self.is_connected = False
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection test failed: {e}")
            self.is_connected = False
            return False
    
    def publish_readings(self, readings_data: Dict[str, Any]) -> bool:
        """
        Send sensor readings to cloud worker
        
        Args:
            readings_data: Dictionary with readings data (from sensor_manager.read_all_sensors())
                Expected format:
                {
                    'timestamp': float (Unix timestamp),
                    'machine_id': int,
                    'company_id': int,
                    'readings': [
                        {
                            'sensor_id': int,
                            'sensor_name': str,
                            'type': str,
                            'data': dict
                        }
                    ]
                }
        
        Returns:
            True if published successfully
        """
        try:
            # Convert to cloud worker format
            payload = self._convert_to_cloud_format(readings_data)
            
            # Send POST request
            url = f"{self.base_url}{self.endpoint}"
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✓ Readings published successfully: {result.get('count', 0)} sensors")
                return True
            else:
                logger.error(f"HTTP POST failed: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"HTTP POST timeout after {self.timeout}s")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP POST error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error publishing readings: {e}")
            return False
    
    def _convert_to_cloud_format(self, readings_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert sensor_manager format to cloud worker format
        
        Args:
            readings_data: Data from sensor_manager.read_all_sensors()
        
        Returns:
            Payload in cloud worker format
        """
        # Handle both Unix timestamp (float) and ISO8601 string formats
        timestamp_raw = readings_data.get('timestamp', datetime.now(timezone.utc).timestamp())
        
        if isinstance(timestamp_raw, str):
            # Already ISO8601 format (from buffer)
            timestamp_iso = timestamp_raw
        elif isinstance(timestamp_raw, (int, float)):
            # Unix timestamp, convert to ISO8601
            timestamp_iso = datetime.fromtimestamp(timestamp_raw, tz=timezone.utc).isoformat()
        else:
            # Fallback to current time
            timestamp_iso = datetime.now(timezone.utc).isoformat()
        
        # Build readings array
        cloud_readings = []
        
        for reading in readings_data.get('readings', []):
            sensor_id = reading.get('sensor_id')
            sensor_type = reading.get('type')
            data = reading.get('data', {})
            
            if sensor_type == 'vibration':
                # Vibration sensor: extract RMS for each axis
                for axis in ['x', 'y', 'z']:
                    vel_key = f'vel_{axis}'
                    if vel_key in data:
                        cloud_readings.append({
                            'sensor_id': sensor_id,
                            'type': 'vibration',
                            'value_rms': data[vel_key],
                            'unit': 'mm/s',
                            'axis': axis
                        })
                
                # Also add gyro if present
                for axis in ['x', 'y', 'z']:
                    gyro_key = f'gyro_{axis}'
                    if gyro_key in data:
                        cloud_readings.append({
                            'sensor_id': sensor_id + 100,  # Offset for gyro
                            'type': 'gyroscope',
                            'value_rms': data[gyro_key],
                            'unit': 'dps',
                            'axis': axis
                        })
            
            elif sensor_type == 'temperature':
                # Temperature sensor
                temperature = data.get('temperature')
                if temperature is not None:
                    cloud_readings.append({
                        'sensor_id': sensor_id,
                        'type': 'temperature',
                        'value': temperature,
                        'unit': 'celsius'
                    })
            
            elif sensor_type == 'current':
                # Current sensor
                current = data.get('current')
                if current is not None:
                    cloud_readings.append({
                        'sensor_id': sensor_id,
                        'type': 'current',
                        'value_rms': current,
                        'unit': 'ampere'
                    })
                
                # Add voltage if present
                voltage = data.get('voltage')
                if voltage is not None:
                    cloud_readings.append({
                        'sensor_id': sensor_id + 200,  # Offset for voltage
                        'type': 'voltage',
                        'value': voltage,
                        'unit': 'volt'
                    })
        
        # Build final payload
        payload = {
            'timestamp': timestamp_iso,
            'machine_id': readings_data.get('machine_id', self.machine_id),
            'company_id': readings_data.get('company_id', self.company_id),
            'readings': cloud_readings,
            'device_info': {
                'device_id': self.device_id
            }
        }
        
        return payload
    
    def disconnect(self):
        """Disconnect (no-op for HTTP)"""
        self.is_connected = False
        logger.info("HTTP client disconnected")
