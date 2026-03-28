"""
Base sensor driver interface.
All sensor drivers must inherit from this class.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging


class SensorDriver(ABC):
    """Abstract base class for all sensor drivers."""
    
    def __init__(self, sensor_id: int, config: Dict[str, Any]):
        """
        Initialize sensor driver.
        
        Args:
            sensor_id: Unique sensor identifier
            config: Sensor configuration dictionary
        """
        self.sensor_id = sensor_id
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.is_initialized = False
        self.initialized = False  # Alias for compatibility
        self.mock_mode = False
        self.error_count = 0
        
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the sensor hardware.
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def read_raw(self) -> Optional[Dict[str, Any]]:
        """
        Read raw data from sensor.
        
        Returns:
            Dictionary with raw sensor data, or None if error
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get sensor status and health information.
        
        Returns:
            Dictionary with status information
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """
        Shutdown sensor and cleanup resources.
        
        Returns:
            True if shutdown successful, False otherwise
        """
        pass
    
    def close(self):
        """Close sensor connection (alias for shutdown)."""
        return self.shutdown()
    
    def reset_error_count(self):
        """Reset the error counter."""
        self.error_count = 0
    
    def increment_error_count(self):
        """Increment the error counter."""
        self.error_count += 1
    
    def get_error_count(self) -> int:
        """Get current error count."""
        return self.error_count
    
    def is_healthy(self) -> bool:
        """
        Check if sensor is healthy (low error count).
        
        Returns:
            True if error count is below threshold
        """
        return self.error_count < 5
