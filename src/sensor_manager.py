"""
Sensor Manager - Manages multiple sensors and data acquisition.
Patched: burst FIFO read, digital filtering, threshold checking.
"""
import json
import logging
import math
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

import numpy as np
from scipy import signal as scipy_signal

from drivers import ISM330DHCXDriver, MAX6675Driver, SCT013ADS1115Driver, SensorDriver


class SensorManager:
    """Manages all sensors and coordinates data acquisition."""

    DRIVER_MAP = {
        'ism330dhcx': ISM330DHCXDriver,
        'max6675': MAX6675Driver,
        'sct013_ads1115': SCT013ADS1115Driver
    }

    def __init__(self, config_path: str):
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path
        self.sensors: Dict[int, SensorDriver] = {}
        self.sensor_configs: List[Dict[str, Any]] = []
        self.is_running = False

        self._load_configuration()
        self.fft_fs = self._get_fft_rate()
        self._design_filters(self.fft_fs)

    def _get_fft_rate(self) -> float:
        """Frequenza del burst vibrazione, letta dal config: fonte unica di verita'."""
        try:
            for s in self.sensor_configs:
                if s.get('type') == 'vibration':
                    r = s.get('processing', {}).get('fft_sampling_rate')
                    if r:
                        return float(r)
        except Exception:
            pass
        return 1660.0

    def _load_configuration(self):
        """Load sensor configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            self.machine_id = config.get('machine_id')
            self.machine_name = config.get('machine_name')
            self.company_id = config.get('company_id')
            self.sensor_configs = config.get('sensors', [])
            self.acquisition_config = config.get('acquisition', {})

            self.logger.info(f"Loaded configuration for machine '{self.machine_name}' "
                           f"(ID: {self.machine_id}) with {len(self.sensor_configs)} sensors")

        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration file: {e}")
            raise

    def _design_filters(self, sampling_rate: float):
        """Design digital filters for vibration signal processing."""
        nyquist = sampling_rate / 2.0
        _f = {}
        try:
            for _s in self.sensor_configs:
                if _s.get('type') == 'vibration':
                    _f = _s.get('processing', {}).get('filters', {})
                    break
        except Exception:
            pass
        hp = min(float(_f.get('highpass', 1.0)), nyquist * 0.5)
        notch = min(float(_f.get('notch', 50.0)), nyquist * 0.9)
        lp = min(float(_f.get('lowpass', 500.0)), nyquist * 0.9)

        # High-pass: remove gravity/DC offset (cutoff 1 Hz)
        self.hp_b, self.hp_a = scipy_signal.butter(4, hp / nyquist, btype='high')

        # Notch: remove 50 Hz power line interference
        self.notch_b, self.notch_a = scipy_signal.iirnotch(notch / nyquist, Q=30)

        # Low-pass: anti-aliasing (cutoff 500 Hz)
        self.lp_b, self.lp_a = scipy_signal.butter(4, lp / nyquist, btype='low')

        self.logger.info(f"Vibration filters designed for {sampling_rate} Hz "
                        f"(HP 1Hz, notch 50Hz, LP 500Hz)")

    def initialize_all_sensors(self) -> bool:
        """Initialize all enabled sensors."""
        success_count = 0

        for sensor_config in self.sensor_configs:
            if not sensor_config.get('enabled', True):
                self.logger.info(f"Sensor {sensor_config['sensor_id']} is disabled, skipping")
                continue

            sensor_id = sensor_config['sensor_id']
            driver_name = sensor_config['driver']

            driver_class = self.DRIVER_MAP.get(driver_name)
            if not driver_class:
                self.logger.error(f"Unknown driver: {driver_name}")
                continue

            try:
                driver = driver_class(sensor_id, sensor_config['config'])

                if driver.initialize():
                    self.sensors[sensor_id] = driver
                    success_count += 1
                    self.logger.info(f"✓ Sensor {sensor_id} ({sensor_config['name']}) initialized")
                else:
                    self.logger.error(f"✗ Failed to initialize sensor {sensor_id}")

            except Exception as e:
                self.logger.error(f"Error initializing sensor {sensor_id}: {e}")

        total_enabled = sum(1 for s in self.sensor_configs if s.get('enabled', True))

        if success_count == total_enabled:
            self.logger.info(f"All {success_count} sensors initialized successfully")
            return True
        else:
            self.logger.warning(f"Only {success_count}/{total_enabled} sensors initialized")
            return False

    def read_all_sensors(self) -> Optional[Dict[str, Any]]:
        """
        Read data from all sensors.
        Vibration: burst mode + digital filtering + RMS + threshold check.
        Temperature: single read + threshold check.
        Current: single read + threshold check.
        """
        readings = []
        timestamp = time.time()

        for sensor_id, driver in self.sensors.items():
            try:
                sensor_config = next(
                    (s for s in self.sensor_configs if s['sensor_id'] == sensor_id),
                    None
                )
                if not sensor_config:
                    continue

                sensor_type = sensor_config.get('type', '')
                raw_data = None

                # --- VIBRATION: burst read + filter + RMS ---
                if sensor_type == 'vibration' and hasattr(driver, 'read_burst'):
                    processing = sensor_config.get('processing', {})
                    fft_samples = processing.get('fft_samples', 1024)

                    self.logger.info(f"Sensor {sensor_id}: burst read ({fft_samples} samples)...")
                    burst_data = driver.read_burst(fft_samples, use_fifo=True)

                    if burst_data and len(burst_data) >= 100:
                        raw_data = self._compute_vibration_stats(burst_data, sensor_config)
                        raw_data['timestamp'] = timestamp

                        status = raw_data.get('status', {})
                        level = status.get('level', '?')
                        self.logger.info(
                            f"Sensor {sensor_id}: [{level.upper()}] RMS "
                            f"x={raw_data.get('accel_x', 0):.4f}g "
                            f"y={raw_data.get('accel_y', 0):.4f}g "
                            f"z={raw_data.get('accel_z', 0):.4f}g "
                            f"({raw_data.get('samples', 0)} samples, filtered)"
                        )
                    else:
                        n = len(burst_data) if burst_data else 0
                        self.logger.warning(
                            f"Sensor {sensor_id}: burst got {n} samples, "
                            f"falling back to single read"
                        )
                        raw_data = driver.read_raw()

                # --- TEMPERATURE: single read + threshold ---
                elif sensor_type == 'temperature':
                    raw_data = driver.read_raw()
                    if raw_data and 'error' not in raw_data:
                        raw_data['status'] = self._check_temperature_threshold(
                            raw_data, sensor_config
                        )
                        level = raw_data['status'].get('level', '?')
                        temp = raw_data.get('temperature')
                        if temp is not None:
                            self.logger.info(
                                f"Sensor {sensor_id}: [{level.upper()}] {temp:.1f}°C"
                            )

                # --- CURRENT: single read + threshold ---
                elif sensor_type == 'current':
                    raw_data = driver.read_raw()
                    if raw_data and 'error' not in raw_data:
                        raw_data['status'] = self._check_current_threshold(
                            raw_data, sensor_config
                        )
                        level = raw_data['status'].get('level', '?')
                        current = raw_data.get('current', 0)
                        self.logger.info(
                            f"Sensor {sensor_id}: [{level.upper()}] {current:.2f}A"
                        )

                else:
                    raw_data = driver.read_raw()

                # --- Append reading ---
                if raw_data and 'error' not in raw_data:
                    reading = {
                        'sensor_id': sensor_id,
                        'sensor_name': sensor_config['name'],
                        'type': sensor_type,
                        'timestamp': raw_data.get('timestamp', timestamp),
                        'data': raw_data
                    }
                    readings.append(reading)
                    driver.reset_error_count()
                else:
                    self.logger.warning(f"No valid data from sensor {sensor_id}")
                    driver.increment_error_count()

                    if not driver.is_healthy():
                        self.logger.error(
                            f"Sensor {sensor_id} unhealthy, attempting recovery"
                        )
                        self._recover_sensor(sensor_id, driver)

            except Exception as e:
                self.logger.error(f"Error reading sensor {sensor_id}: {e}")

        if not readings:
            self.logger.error("No sensor readings available")
            return None

        return {
            'timestamp': timestamp,
            'machine_id': self.machine_id,
            'company_id': self.company_id,
            'readings': readings
        }

    # ------------------------------------------------------------------
    #  Vibration processing
    # ------------------------------------------------------------------

    def _compute_vibration_stats(self, samples: list,
                                  sensor_config: dict = None) -> dict:
        """
        Compute RMS, peak, peak-to-peak from burst samples.
        Applies HP 1Hz + notch 50Hz + LP 500Hz before statistics.
        """
        result = {}

        for axis in ['accel_x', 'accel_y', 'accel_z']:
            values = [s[axis] for s in samples if axis in s]
            if not values:
                continue

            data = np.array(values, dtype=np.float64)

            # Apply digital filters
            try:
                data = scipy_signal.filtfilt(self.hp_b, self.hp_a, data)
                data = scipy_signal.filtfilt(self.notch_b, self.notch_a, data)
                data = scipy_signal.filtfilt(self.lp_b, self.lp_a, data)
            except Exception as e:
                self.logger.warning(f"Filter failed for {axis}: {e}, using raw data")
                data = np.array(values, dtype=np.float64)

            rms = float(np.sqrt(np.mean(data ** 2)))
            peak = float(np.max(np.abs(data)))
            p2p = float(np.max(data) - np.min(data))

            # accel RMS in g (tenuto per diagnosi cuscinetti in alta frequenza)
            result[axis] = round(rms, 6)
            result[f'{axis}_peak'] = round(peak, 6)
            result[f'{axis}_p2p'] = round(p2p, 6)
            # velocita RMS in mm/s (ISO 10816) da campioni GREZZI, non filtrati
            result[axis.replace('accel_', 'vel_')] = self._velocity_rms_mms(values)

        result['samples'] = len(samples)
        result['unit'] = 'g'
        result['measurement'] = 'burst_rms_filtered'

        if sensor_config:
            result['status'] = self._check_vibration_thresholds(result, sensor_config)

        return result

    def _velocity_rms_mms(self, accel_g, fs: float = None,
                          f_lo: float = 10.0, f_hi: float = None) -> float:
        """Velocita RMS in mm/s: integrazione in frequenza band-limited (ISO 10816)."""
        import numpy as _np
        if fs is None:
            fs = getattr(self, 'fft_fs', 1660.0)
        if f_hi is None:
            f_hi = min(800.0, fs / 2.1)
        x = _np.asarray(accel_g, dtype=_np.float64) * 9.80665   # g -> m/s^2
        x = x - _np.mean(x)
        N = len(x)
        if N < 8:
            return 0.0
        w = _np.hanning(N)
        spec = _np.fft.rfft(x * w)
        fr = _np.fft.rfftfreq(N, d=1.0 / fs)
        vspec = _np.zeros_like(spec)
        band = (fr >= f_lo) & (fr <= f_hi)
        vspec[band] = spec[band] / (1j * 2 * _np.pi * fr[band])
        v = _np.fft.irfft(vspec, n=N)
        w_rms = _np.sqrt(_np.mean(w ** 2))
        return round(float(_np.sqrt(_np.mean(v ** 2)) / w_rms) * 1000.0, 4)

    def _check_vibration_thresholds(self, stats: dict,
                                     sensor_config: dict) -> dict:
        """Check vibration RMS against warning/critical thresholds."""
        thresholds = sensor_config.get('thresholds', {})
        warning_rms = thresholds.get('warning', {}).get('accel_rms', float('inf'))
        critical_rms = thresholds.get('critical', {}).get('accel_rms', float('inf'))

        max_rms = 0.0
        for axis in ['accel_x', 'accel_y', 'accel_z']:
            if axis in stats:
                max_rms = max(max_rms, stats[axis])

        if max_rms >= critical_rms:
            level = 'critical'
            message = f"Vibrazione critica: RMS {max_rms:.4f}g supera soglia {critical_rms}g"
        elif max_rms >= warning_rms:
            level = 'warning'
            message = f"Vibrazione elevata: RMS {max_rms:.4f}g supera soglia {warning_rms}g"
        else:
            level = 'normal'
            message = f"Vibrazione nella norma: RMS {max_rms:.4f}g"

        return {
            'level': level,
            'max_rms': round(max_rms, 6),
            'warning_threshold': warning_rms,
            'critical_threshold': critical_rms,
            'message': message
        }

    # ------------------------------------------------------------------
    #  Temperature threshold
    # ------------------------------------------------------------------

    def _check_temperature_threshold(self, data: dict,
                                      sensor_config: dict) -> dict:
        """Check temperature against warning/critical thresholds."""
        thresholds = sensor_config.get('thresholds', {})
        warning_temp = thresholds.get('warning', {}).get('temperature', float('inf'))
        critical_temp = thresholds.get('critical', {}).get('temperature', float('inf'))

        temp = data.get('temperature')
        if temp is None:
            return {'level': 'error', 'message': 'Termocoppia disconnessa'}

        if temp >= critical_temp:
            level = 'critical'
            message = f"Temperatura critica: {temp:.1f}°C supera soglia {critical_temp}°C"
        elif temp >= warning_temp:
            level = 'warning'
            message = f"Temperatura elevata: {temp:.1f}°C supera soglia {warning_temp}°C"
        else:
            level = 'normal'
            message = f"Temperatura nella norma: {temp:.1f}°C"

        return {
            'level': level,
            'value': temp,
            'warning_threshold': warning_temp,
            'critical_threshold': critical_temp,
            'message': message
        }

    # ------------------------------------------------------------------
    #  Current threshold
    # ------------------------------------------------------------------

    def _check_current_threshold(self, data: dict,
                                  sensor_config: dict) -> dict:
        """Check current RMS against warning/critical thresholds."""
        thresholds = sensor_config.get('thresholds', {})
        warning_current = thresholds.get('warning', {}).get('current_rms', float('inf'))
        critical_current = thresholds.get('critical', {}).get('current_rms', float('inf'))

        current = data.get('current', 0)

        if current >= critical_current:
            level = 'critical'
            message = f"Corrente critica: {current:.2f}A supera soglia {critical_current}A"
        elif current >= warning_current:
            level = 'warning'
            message = f"Corrente elevata: {current:.2f}A supera soglia {warning_current}A"
        else:
            level = 'normal'
            message = f"Corrente nella norma: {current:.2f}A"

        return {
            'level': level,
            'value': current,
            'warning_threshold': warning_current,
            'critical_threshold': critical_current,
            'message': message
        }

    # ------------------------------------------------------------------
    #  Recovery, status, lifecycle
    # ------------------------------------------------------------------

    def _recover_sensor(self, sensor_id: int, driver: SensorDriver):
        """Attempt to recover a failed sensor."""
        try:
            self.logger.info(f"Attempting to recover sensor {sensor_id}")
            driver.close()
            time.sleep(1)

            if driver.initialize():
                driver.reset_error_count()
                self.logger.info(f"Sensor {sensor_id} recovered successfully")
            else:
                self.logger.error(f"Failed to recover sensor {sensor_id}")

        except Exception as e:
            self.logger.error(f"Error recovering sensor {sensor_id}: {e}")

    def get_sensor_status(self) -> Dict[str, Any]:
        """Get status of all sensors."""
        sensors_status = []

        for sensor_id, driver in self.sensors.items():
            sensor_config = next(
                (s for s in self.sensor_configs if s['sensor_id'] == sensor_id),
                None
            )

            if sensor_config:
                status = {
                    'sensor_id': sensor_id,
                    'name': sensor_config['name'],
                    'type': sensor_config['type'],
                    'is_initialized': driver.is_initialized,
                    'is_healthy': driver.is_healthy(),
                    'error_count': driver.get_error_count()
                }
                sensors_status.append(status)

        return {
            'machine_id': self.machine_id,
            'total_sensors': len(self.sensors),
            'healthy_sensors': sum(1 for s in sensors_status if s['is_healthy']),
            'sensors': sensors_status
        }

    def close_all_sensors(self):
        """Close all sensor connections."""
        for sensor_id, driver in self.sensors.items():
            try:
                driver.close()
                self.logger.info(f"Sensor {sensor_id} closed")
            except Exception as e:
                self.logger.error(f"Error closing sensor {sensor_id}: {e}")

        self.sensors.clear()
        self.logger.info("All sensors closed")

    def get_read_interval(self) -> int:
        """Get configured read interval in seconds."""
        return self.acquisition_config.get('read_interval', 30)

    def is_acquisition_enabled(self) -> bool:
        """Check if data acquisition is enabled."""
        return self.acquisition_config.get('enabled', True)
