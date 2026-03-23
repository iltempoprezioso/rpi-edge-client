"""
Data Processor - Applies filters and calculations to sensor data.
"""
import logging
import math
from typing import Dict, List, Any, Optional
import numpy as np
from scipy import signal


class DataProcessor:
    """Processes raw sensor data with filters and calculations."""
    
    def __init__(self, sampling_rate: float = 1600.0):
        """
        Initialize data processor.
        
        Args:
            sampling_rate: Sampling rate in Hz for signal processing
        """
        self.logger = logging.getLogger(__name__)
        self.sampling_rate = sampling_rate
        
        # Design filters
        self._design_filters()
    
    def _design_filters(self):
        """Design digital filters for signal processing."""
        nyquist = self.sampling_rate / 2.0
        
        # High-pass filter (remove DC offset, cutoff 1 Hz)
        self.highpass_b, self.highpass_a = signal.butter(
            4, 1.0 / nyquist, btype='high'
        )
        
        # Low-pass filter (anti-aliasing, cutoff 500 Hz)
        self.lowpass_b, self.lowpass_a = signal.butter(
            4, 500.0 / nyquist, btype='low'
        )
        
        # Notch filter (remove power line interference, 50 Hz)
        self.notch_b, self.notch_a = signal.iirnotch(
            50.0 / nyquist, Q=30
        )
        
        self.logger.info(f"Filters designed for sampling rate {self.sampling_rate} Hz")
    
    def process_vibration_data(self, raw_data: List[Dict[str, Any]], 
                               config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process vibration sensor data.
        
        Args:
            raw_data: List of raw sensor readings
            config: Processing configuration from sensor config
            
        Returns:
            Processed data with RMS, peak-to-peak, etc.
        """
        try:
            if not raw_data:
                return {}
            
            # Extract acceleration values for each axis
            axes = config.get('config', {}).get('axes', ['x', 'y', 'z'])
            results = {}
            
            for axis in axes:
                # Extract axis data
                axis_values = [reading.get(axis, 0) for reading in raw_data]
                
                # Convert g to mm/s (multiply by 9.81 * 1000)
                axis_values_mms = [v * 9810.0 for v in axis_values]
                
                # Apply filters if configured
                filtered_data = self._apply_filters(axis_values_mms, config)
                
                # Calculate metrics
                rms = self._calculate_rms(filtered_data)
                peak_to_peak = self._calculate_peak_to_peak(filtered_data)
                peak = max(abs(min(filtered_data)), abs(max(filtered_data)))
                
                results[axis] = {
                    'rms': round(rms, 3),
                    'peak_to_peak': round(peak_to_peak, 3),
                    'peak': round(peak, 3),
                    'unit': 'mm/s'
                }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing vibration data: {e}")
            return {}
    
    def process_temperature_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process temperature sensor data.
        
        Args:
            raw_data: Raw temperature reading
            
        Returns:
            Processed temperature data
        """
        try:
            return {
                'value': raw_data.get('temperature', 0),
                'internal_temp': raw_data.get('internal_temp', 0),
                'unit': 'celsius'
            }
        except Exception as e:
            self.logger.error(f"Error processing temperature data: {e}")
            return {}
    
    def process_current_data(self, raw_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process current sensor data with advanced metrics.
        
        Args:
            raw_samples: List of current readings
            
        Returns:
            Processed current data with RMS, power estimation, and anomaly metrics
        """
        try:
            if not raw_samples:
                return {}
            
            # Extract current values
            current_values = [reading.get('current', 0) for reading in raw_samples]
            
            # Calculate RMS
            rms = self._calculate_rms(current_values)
            
            # Calculate peak and average
            peak = max(current_values)
            avg = sum(current_values) / len(current_values)
            
            # Calculate crest factor (peak/RMS) - indicator of signal quality
            crest_factor = peak / rms if rms > 0 else 0
            
            # Calculate coefficient of variation (std/mean) - stability indicator
            std = math.sqrt(sum((x - avg)**2 for x in current_values) / len(current_values))
            cv = (std / avg * 100) if avg > 0 else 0
            
            # Estimate power (assuming 230V AC, single phase)
            # P = V * I * power_factor (assuming PF = 0.85 typical for motors)
            estimated_power = 230 * rms * 0.85
            
            return {
                'rms': round(rms, 3),
                'peak': round(peak, 3),
                'average': round(avg, 3),
                'crest_factor': round(crest_factor, 2),
                'stability_cv': round(cv, 1),  # Lower is better
                'estimated_power_w': round(estimated_power, 0),
                'unit': 'ampere'
            }
            
        except Exception as e:
            self.logger.error(f"Error processing current data: {e}")
            return {}
    
    def detect_current_anomalies(self, current_rms: float, 
                                 baseline: float, 
                                 tolerance: float = 0.15) -> Dict[str, Any]:
        """
        Detect anomalies in current consumption.
        
        Args:
            current_rms: Current RMS value
            baseline: Baseline (normal) current value
            tolerance: Acceptable deviation (default 15%)
            
        Returns:
            Anomaly detection results
        """
        try:
            deviation = abs(current_rms - baseline) / baseline if baseline > 0 else 0
            
            if deviation > tolerance * 2:
                severity = 'critical'
                message = f"Current {current_rms}A deviates {deviation*100:.1f}% from baseline {baseline}A"
            elif deviation > tolerance:
                severity = 'warning'
                message = f"Current {current_rms}A slightly elevated ({deviation*100:.1f}% deviation)"
            else:
                severity = 'normal'
                message = f"Current within normal range ({deviation*100:.1f}% deviation)"
            
            return {
                'severity': severity,
                'deviation_percent': round(deviation * 100, 1),
                'message': message,
                'current_rms': current_rms,
                'baseline': baseline
            }
            
        except Exception as e:
            self.logger.error(f"Error detecting current anomalies: {e}")
            return {}
    
    def _apply_filters(self, data: List[float], config: Dict[str, Any]) -> List[float]:
        """
        Apply configured filters to data.
        
        Args:
            data: Input signal
            config: Sensor configuration with filter settings
            
        Returns:
            Filtered signal
        """
        filters = config.get('processing', {}).get('filters', [])
        
        filtered = np.array(data)
        
        if 'highpass_1hz' in filters:
            filtered = signal.filtfilt(self.highpass_b, self.highpass_a, filtered)
        
        if 'lowpass_500hz' in filters:
            filtered = signal.filtfilt(self.lowpass_b, self.lowpass_a, filtered)
        
        if 'notch_50hz' in filters:
            filtered = signal.filtfilt(self.notch_b, self.notch_a, filtered)
        
        return filtered.tolist()
    
    def _calculate_rms(self, data: List[float]) -> float:
        """
        Calculate Root Mean Square.
        
        Args:
            data: Input signal
            
        Returns:
            RMS value
        """
        if not data:
            return 0.0
        
        sum_squares = sum(x**2 for x in data)
        rms = math.sqrt(sum_squares / len(data))
        return rms
    
    def _calculate_peak_to_peak(self, data: List[float]) -> float:
        """
        Calculate peak-to-peak amplitude.
        
        Args:
            data: Input signal
            
        Returns:
            Peak-to-peak value
        """
        if not data:
            return 0.0
        
        return max(data) - min(data)
    
    def calculate_fft(self, data: List[float]) -> Dict[str, Any]:
        """
        Calculate FFT spectrum (for future use).
        
        Args:
            data: Input signal
            
        Returns:
            Dictionary with frequencies and magnitudes
        """
        try:
            # Perform FFT
            fft_values = np.fft.rfft(data)
            fft_magnitude = np.abs(fft_values)
            fft_freq = np.fft.rfftfreq(len(data), 1.0 / self.sampling_rate)
            
            return {
                'frequencies': fft_freq.tolist(),
                'magnitudes': fft_magnitude.tolist()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating FFT: {e}")
            return {}
    
    def check_threshold(self, value: float, thresholds: Dict[str, float]) -> str:
        """
        Check if value exceeds thresholds.
        
        Args:
            value: Measured value
            thresholds: Dictionary with 'warning' and 'critical' thresholds
            
        Returns:
            Status: 'normal', 'warning', or 'critical'
        """
        critical = thresholds.get('critical', float('inf'))
        warning = thresholds.get('warning', float('inf'))
        
        if value >= critical:
            return 'critical'
        elif value >= warning:
            return 'warning'
        else:
            return 'normal'
