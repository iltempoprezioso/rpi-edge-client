#!/usr/bin/env python3
"""
Retry utilities for robust hardware communication
Handles transient I2C/SPI errors in industrial environments
"""

import time
import functools
import logging

logger = logging.getLogger(__name__)


def i2c_retry(max_retries=3, delay=0.05, backoff=1.5):
    """
    Decorator to retry I2C operations on transient errors
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
    
    Usage:
        @i2c_retry(max_retries=3, delay=0.05)
        def read_sensor(self):
            return self.bus.read_byte_data(addr, reg)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OSError, IOError) as e:
                    last_error = e
                    
                    if attempt < max_retries - 1:
                        # Get sensor_id from self if available
                        sensor_id = getattr(args[0], 'sensor_id', 'unknown') if args else 'unknown'
                        logger.warning(
                            f"Sensor {sensor_id}: I2C error on attempt {attempt + 1}/{max_retries}: {e}. "
                            f"Retrying in {current_delay:.3f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"Sensor {sensor_id}: I2C operation failed after {max_retries} attempts: {e}"
                        )
            
            # All retries exhausted
            raise last_error
        
        return wrapper
    return decorator


def spi_retry(max_retries=3, delay=0.01):
    """
    Decorator to retry SPI operations on transient errors
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries (seconds)
    
    Usage:
        @spi_retry(max_retries=3)
        def read_sensor(self):
            return self.spi.xfer2([0x00, 0x00])
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OSError, IOError) as e:
                    last_error = e
                    
                    if attempt < max_retries - 1:
                        sensor_id = getattr(args[0], 'sensor_id', 'unknown') if args else 'unknown'
                        logger.warning(
                            f"Sensor {sensor_id}: SPI error on attempt {attempt + 1}/{max_retries}: {e}. "
                            f"Retrying in {delay:.3f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Sensor {sensor_id}: SPI operation failed after {max_retries} attempts: {e}"
                        )
            
            raise last_error
        
        return wrapper
    return decorator
