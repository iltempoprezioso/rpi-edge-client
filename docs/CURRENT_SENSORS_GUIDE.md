# Sensori di Corrente Elettrica - Guida Integrazione

## 🔌 Panoramica

L'integrazione di sensori di corrente/potenza per motori elettrici è **fondamentale** per un sistema completo di predictive maintenance industriale.

---

## ✅ VANTAGGI CHIAVE

### 1. Early Fault Detection
- **Sovraccarico meccanico**: Corrente ↑ → possibile blocco/inceppamento
- **Usura cuscinetti**: Drift corrente nel tempo
- **Sbilanciamento**: Oscillazioni corrente → problema rotore/statore
- **Guasti avvolgimenti**: Pattern anomali corrente

### 2. Correlazione Multi-Sensore
```
🔍 Pattern Diagnostici:

Cuscinetto Danneggiato:
- Vibrazioni: ↑ 150% (picchi a frequenze specifiche)
- Temperatura: ↑ 15°C
- Corrente: ↑ 20% + oscillazioni

Trasmissione Rotta:
- Vibrazioni: ↓↓ (assenza vibrazione operativa)
- Temperatura: → stabile
- Corrente: ↓↓ 50% (motore gira a vuoto)

Sovraccarico Lavorazione:
- Vibrazioni: ↑ 80%
- Temperatura: ↑ 25°C
- Corrente: ↑ 40% + picchi
```

### 3. Energy Monitoring & ROI
- **Costo energetico**: kWh reali per macchina/processo
- **Efficienza drift**: Degrado prestazioni nel tempo
- **OEE (Overall Equipment Effectiveness)**: kWh/pezzo prodotto
- **ROI immediato**: Riduzione costi energia 5-15%

### 4. Machine Learning Ready
Corrente elettrica = **miglior input ML** per predictive maintenance:
- ✅ Misura non invasiva
- ✅ Alta correlazione con stato meccanico
- ✅ Campionamento continuo facile
- ✅ Basso rumore elettronico

---

## 📊 SENSORI CONSIGLIATI

### Opzione 1: ACS712 (✅ GIÀ IMPLEMENTATO)

**Specifiche**:
- Range: 5A, 20A, 30A (modelli diversi)
- Interfaccia: Analogico (via ADC MCP3008)
- Precisione: ±1.5% a 25°C
- Bandwidth: 80 kHz
- Isolation: 2.1 kV RMS

**Vantaggi**:
- ✅ Già implementato nel progetto
- ✅ Economico (~$2)
- ✅ Facile integrazione
- ✅ Hall-effect (isolato)

**Limitazioni**:
- ⚠️ Solo corrente RMS
- ⚠️ No misura tensione
- ⚠️ No power factor
- ⚠️ No energia cumulativa

**Uso ideale**:
- Motori DC
- Motori AC monofase
- Proof-of-concept
- Budget limitato

---

### Opzione 2: PZEM-004T v3.0 (⭐ CONSIGLIATO)

**Specifiche**:
- Tensione: 80-260V AC
- Corrente: 0-100A
- Potenza: 0-22 kW
- Energia: 0-9999.99 kWh
- Frequenza: 45-65 Hz
- Power Factor: 0.00-1.00
- Interfaccia: UART/Modbus RTU
- Precisione: ±0.5% (Classe 1)

**Vantaggi**:
- ✅ Misura **Potenza Attiva** (W)
- ✅ Misura **Energia cumulativa** (kWh)
- ✅ Misura **Power Factor**
- ✅ Economico (~$10-15)
- ✅ Certificato CE
- ✅ Installazione su quadro elettrico

**Implementazione**:
```python
# drivers/pzem004t.py
import serial
import struct
import time
from .base_driver import SensorDriver

class PZEM004TDriver(SensorDriver):
    """
    Driver for PZEM-004T v3.0 AC Power Meter.
    Modbus RTU interface via UART.
    """
    
    MODBUS_ADDRESS = 0x01
    BAUD_RATE = 9600
    
    def __init__(self, sensor_id: int, config: dict):
        super().__init__(sensor_id, config)
        self.port = config.get('uart_port', '/dev/ttyUSB0')
        self.serial = None
    
    def initialize(self) -> bool:
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.BAUD_RATE,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1.0
            )
            self.is_initialized = True
            self.logger.info(f"PZEM-004T initialized on {self.port}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize PZEM-004T: {e}")
            return False
    
    def read_raw(self) -> dict:
        """Read all electrical parameters."""
        try:
            # Modbus RTU: Read Input Registers (0x04)
            # Start address: 0x0000, Registers: 10
            command = bytes([
                self.MODBUS_ADDRESS,  # Slave address
                0x04,                  # Function code
                0x00, 0x00,           # Start address
                0x00, 0x0A            # Number of registers
            ])
            
            # Calculate CRC
            crc = self._calculate_crc(command)
            command += crc
            
            # Send command
            self.serial.write(command)
            time.sleep(0.1)
            
            # Read response
            response = self.serial.read(25)
            
            if len(response) < 25:
                self.logger.error("Incomplete response from PZEM-004T")
                return None
            
            # Parse response
            data = struct.unpack('>HHHHHHHHHH', response[3:23])
            
            voltage = data[0] / 10.0          # V
            current = (data[1] + (data[2] << 16)) / 1000.0  # A
            power = (data[3] + (data[4] << 16)) / 10.0      # W
            energy = data[5] + (data[6] << 16)  # Wh
            frequency = data[7] / 10.0        # Hz
            power_factor = data[8] / 100.0    # PF
            alarm = data[9]                    # Alarm status
            
            result = {
                'timestamp': time.time(),
                'voltage': round(voltage, 1),
                'current': round(current, 3),
                'power': round(power, 1),
                'energy': round(energy / 1000.0, 2),  # Convert to kWh
                'frequency': round(frequency, 1),
                'power_factor': round(power_factor, 2),
                'alarm': alarm,
                'unit_voltage': 'volt',
                'unit_current': 'ampere',
                'unit_power': 'watt',
                'unit_energy': 'kwh'
            }
            
            self.reset_error_count()
            return result
            
        except Exception as e:
            self.logger.error(f"Error reading PZEM-004T: {e}")
            self.increment_error_count()
            return None
    
    def _calculate_crc(self, data: bytes) -> bytes:
        """Calculate Modbus CRC16."""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return struct.pack('<H', crc)
    
    def close(self):
        if self.serial:
            self.serial.close()
        self.is_initialized = False
```

**Configurazione sensori.json**:
```json
{
  "sensor_id": 4,
  "name": "Power Meter Motore Principale",
  "type": "power",
  "driver": "pzem004t",
  "interface": "uart",
  "enabled": true,
  "config": {
    "uart_port": "/dev/ttyUSB0",
    "modbus_address": 1
  },
  "processing": {
    "calculations": ["average", "peak"],
    "output_units": ["volt", "ampere", "watt", "kwh"]
  },
  "thresholds": {
    "current": {
      "warning": 25,
      "critical": 28
    },
    "power_factor": {
      "warning": 0.7,
      "critical": 0.6
    }
  }
}
```

---

### Opzione 3: SCT-013 (Current Transformer)

**Specifiche**:
- Range: 0-30A, 0-100A (modelli vari)
- Output: 0-1V AC o 0-50mA AC
- Non invasivo (clamp-on)
- Accuracy: ±1%

**Vantaggi**:
- ✅ Installazione **senza taglio cavi**
- ✅ Sicurezza (isolamento galvanico)
- ✅ Economico (~$5)
- ✅ Ideale retrofit impianti esistenti

**Limitazioni**:
- ⚠️ Solo corrente (no V, no PF)
- ⚠️ Calibrazione necessaria
- ⚠️ Sensibile a posizione cavo

**Implementazione**:
```python
# Uso con ADC esterno (es. ADS1115)
class SCT013Driver(SensorDriver):
    """Driver for SCT-013 Current Transformer."""
    
    def read_raw(self) -> dict:
        # Leggi tensione ADC (0-1V rappresenta 0-30A)
        adc_voltage = self.read_adc()
        
        # Calibrazione: 1V = 30A
        current = adc_voltage * 30.0
        
        # Calcola RMS da campioni
        samples = self.read_samples(100)
        current_rms = self._calculate_rms(samples)
        
        return {
            'timestamp': time.time(),
            'current': current_rms,
            'unit': 'ampere'
        }
```

---

### Opzione 4: INA219/INA226 (Per DC)

**Specifiche (INA226)**:
- Tensione: 0-36V
- Corrente: ±20A (con shunt 0.1Ω)
- Interfaccia: I2C
- Precisione: ±0.1%
- 16-bit ADC

**Uso ideale**:
- Motori DC (CNC, robot)
- Motori stepper
- Alimentatori switching
- Misure alta precisione

---

## 🔥 CASI D'USO PRATICI

### Caso 1: Centro Lavoro CNC

**Setup**:
```json
{
  "machine_name": "Centro Lavoro CNC Haas VF-2",
  "sensors": [
    {
      "sensor_id": 1,
      "name": "Vibrazioni Mandrino",
      "type": "vibration",
      "driver": "adxl345"
    },
    {
      "sensor_id": 2,
      "name": "Temperatura Cuscinetti",
      "type": "temperature",
      "driver": "max31855"
    },
    {
      "sensor_id": 3,
      "name": "Potenza Mandrino",
      "type": "power",
      "driver": "pzem004t",
      "baseline_current": 8.5,
      "baseline_power": 1955
    }
  ]
}
```

**Pattern Diagnostici**:
```python
# Pattern 1: Utensile rotto/usurato
if current > baseline * 1.3 and vibration > threshold:
    alert("Utensile danneggiato - sostituire")

# Pattern 2: Cuscinetti usurati
if drift_current_6months > 15% and temp_increase > 10:
    alert("Cuscinetti mandrino da sostituire")

# Pattern 3: Sovraccarico lavorazione
if power > baseline * 1.5:
    alert("Parametri taglio troppo aggressivi")

# Pattern 4: Power factor basso
if power_factor < 0.75:
    alert("Motore inefficiente - verificare condensatori")
```

---

### Caso 2: Pompa Centrifuga

**Setup**:
- Vibrazioni: ADXL345
- Temperatura olio: MAX31855
- **Corrente motore**: ACS712 o PZEM-004T

**KPI Monitorati**:
```python
# Efficienza energetica
kWh_per_m3 = energy_consumed / volume_pumped

# Curve caratteristiche
flow_vs_power = {
    '100%': 5.5,  # kW @ 100% portata
    '75%': 3.2,   # kW @ 75% portata
    '50%': 1.8    # kW @ 50% portata
}

# Anomaly detection
if current_power > expected_power * 1.2:
    alert("Filtri intasati o cavitazione")
```

---

### Caso 3: Compressore Aria

**Setup**:
- Vibrazioni
- Temperatura aria uscita
- **Potenza elettrica**: PZEM-004T
- **Pressione**: (sensore aggiuntivo)

**Dashboard Metriche**:
```
┌─────────────────────────────────────┐
│  Compressore - Real-time Metrics   │
├─────────────────────────────────────┤
│ Potenza:          7.2 kW            │
│ Corrente:         31.2 A            │
│ Power Factor:     0.82              │
│                                      │
│ Pressione:        8.5 bar           │
│ Temperatura:      85°C              │
│ Vibrazioni:       3.1 mm/s RMS      │
│                                      │
│ Energia oggi:     58.3 kWh          │
│ Costo energia:    €8.75             │
│ kWh per m³ aria:  0.12 kWh/m³       │
│ Efficienza:       92% ✅            │
└─────────────────────────────────────┘

Trend 30 giorni:
kWh/m³: 0.10 → 0.12 (+20%) ⚠️
→ Compressore perde efficienza
→ Programmare manutenzione
```

---

## 📈 METRICHE E ALGORITMI

### 1. Baseline Learning
```python
def learn_baseline(sensor_id: int, days: int = 30):
    """
    Impara baseline corrente/potenza normale.
    Usa mediana per robustezza a outlier.
    """
    readings = get_historical_data(sensor_id, days=days)
    
    # Filtra solo cicli operativi (machine ON)
    operational = [r for r in readings if r['status'] == 'running']
    
    currents = [r['current'] for r in operational]
    powers = [r['power'] for r in operational]
    
    baseline = {
        'current_median': np.median(currents),
        'current_std': np.std(currents),
        'power_median': np.median(powers),
        'power_std': np.std(powers),
        'samples': len(operational)
    }
    
    return baseline
```

### 2. Drift Detection
```python
def detect_drift(current_value: float, baseline: dict, window_days: int = 90):
    """
    Rileva drift lento nel tempo (usura graduale).
    """
    historical = get_historical_data(window_days)
    
    # Linear regression su ultimi 90 giorni
    from scipy.stats import linregress
    
    days = list(range(len(historical)))
    values = [r['current'] for r in historical]
    
    slope, intercept, r_value, p_value, std_err = linregress(days, values)
    
    # Slope positivo significativo = drift
    if slope > 0 and p_value < 0.05:
        drift_percent = (slope * window_days) / baseline['current_median'] * 100
        
        if drift_percent > 15:
            return {
                'status': 'critical',
                'drift_percent': drift_percent,
                'message': f"Corrente aumentata {drift_percent:.1f}% in {window_days} giorni"
            }
        elif drift_percent > 8:
            return {
                'status': 'warning',
                'drift_percent': drift_percent,
                'message': f"Drift corrente rilevato: +{drift_percent:.1f}%"
            }
    
    return {'status': 'normal'}
```

### 3. Current Signature Analysis
```python
def analyze_current_signature(samples: List[float], sampling_rate: float = 1000):
    """
    Analisi FFT corrente motore (MCSA - Motor Current Signature Analysis).
    Rileva guasti cuscinetti, barre rotore rotte, eccentricità.
    """
    from scipy.fft import fft, fftfreq
    
    # FFT
    fft_values = fft(samples)
    fft_freq = fftfreq(len(samples), 1/sampling_rate)
    fft_magnitude = np.abs(fft_values)
    
    # Frequenza linea elettrica (50 Hz)
    f_line = 50  # Hz
    
    # Frequenze slip (f_line ± s*f_rotor)
    # Indicano barre rotore rotte
    slip_freq_lower = f_line - 2  # 48 Hz
    slip_freq_upper = f_line + 2  # 52 Hz
    
    # Cerca picchi a frequenze slip
    slip_magnitude_lower = get_fft_magnitude_at_freq(fft_freq, fft_magnitude, slip_freq_lower)
    slip_magnitude_upper = get_fft_magnitude_at_freq(fft_freq, fft_magnitude, slip_freq_upper)
    
    # Baseline a 50 Hz
    baseline_magnitude = get_fft_magnitude_at_freq(fft_freq, fft_magnitude, f_line)
    
    # Ratio slip/baseline
    slip_ratio = (slip_magnitude_lower + slip_magnitude_upper) / baseline_magnitude
    
    if slip_ratio > 0.1:
        return {
            'fault': 'broken_rotor_bars',
            'severity': 'critical',
            'slip_ratio': slip_ratio
        }
    
    return {'fault': 'none'}
```

---

## 🚀 IMPLEMENTAZIONE NEL PROGETTO

### Step 1: Aggiungi driver PZEM-004T

Creo il nuovo driver:

```bash
# File: drivers/pzem004t.py
# (codice sopra)
```

### Step 2: Aggiorna sensor_manager.py

```python
# src/sensor_manager.py
DRIVER_MAP = {
    'adxl345': ADXL345Driver,
    'max31855': MAX31855Driver,
    'acs712': ACS712Driver,
    'pzem004t': PZEM004TDriver  # ← NUOVO
}
```

### Step 3: Configura sensore

```json
// config/sensors.json
{
  "sensor_id": 4,
  "name": "Power Meter Motore",
  "type": "power",
  "driver": "pzem004t",
  "enabled": true,
  "config": {
    "uart_port": "/dev/ttyUSB0"
  }
}
```

### Step 4: Test

```bash
cd /home/user/webapp/rpi-edge-client
source venv/bin/activate

python3 -c "
from drivers.pzem004t import PZEM004TDriver
sensor = PZEM004TDriver(4, {'uart_port': '/dev/ttyUSB0'})
if sensor.initialize():
    data = sensor.read_raw()
    print(data)
"
```

---

## 💰 ANALISI COSTI/BENEFICI

### Investimento Hardware

| Sensore | Costo | Metriche | Ideale Per |
|---------|-------|----------|------------|
| ACS712 | €2 | Corrente | POC, DC motors |
| SCT-013 | €5 | Corrente | Retrofit facile |
| PZEM-004T | €12 | V, A, W, kWh, PF | AC motors (best) |
| INA226 | €8 | V, A (DC) | Alta precisione DC |

### ROI Tipico

```
Scenario: Impianto con 10 macchine CNC

Investimento:
- 10× PZEM-004T: €120
- 10× Raspberry Pi (già presente): €0
- Installazione: €200
TOTALE: €320

Risparmi Anno 1:
1. Energy monitoring:
   - Riduzione consumi 8%: €2,400/anno
   
2. Predictive maintenance:
   - Riduzione downtime 15%: €5,000/anno
   - Meno guasti critici: €3,000/anno
   
TOTALE RISPARMI: €10,400/anno

ROI: (10,400 - 320) / 320 = 3,150%
Payback: 11 giorni ✅
```

---

## 📊 DASHBOARD ESEMPIO

```
┌────────────────────────────────────────────┐
│  Machine Health - Real-time Monitoring    │
├────────────────────────────────────────────┤
│                                             │
│  🔋 Electrical                             │
│  ├─ Voltage:        228.3 V     ✅         │
│  ├─ Current:        12.4 A      ✅         │
│  ├─ Power:          2,834 W     ✅         │
│  ├─ Power Factor:   0.92        ✅         │
│  └─ Energy Today:   58.3 kWh              │
│                                             │
│  📊 Vibration                              │
│  ├─ X-axis:         2.1 mm/s    ✅         │
│  ├─ Y-axis:         1.8 mm/s    ✅         │
│  └─ Z-axis:         3.2 mm/s    ⚠️         │
│                                             │
│  🌡️ Temperature                            │
│  ├─ Bearing Front:  68°C        ✅         │
│  └─ Bearing Rear:   71°C        ✅         │
│                                             │
│  📈 Trends (30 days)                       │
│  ├─ Power drift:    +3.2%       →          │
│  ├─ Vibration:      +12%        ⚠️         │
│  └─ Temperature:    +8°C        ⚠️         │
│                                             │
│  🎯 Recommendations                        │
│  • Schedule bearing inspection             │
│  • Check Z-axis alignment                  │
│  • Energy efficiency: 94% (Good)           │
│                                             │
└────────────────────────────────────────────┘
```

---

## ✅ CONCLUSIONE

**SÌ, INTEGRA ASSOLUTAMENTE I SENSORI DI CORRENTE!**

### Raccomandazioni:

1. **Per POC/Budget**: Usa **ACS712** (già implementato) ✅
2. **Per Produzione**: Upgrade a **PZEM-004T** ⭐⭐⭐⭐⭐
3. **Per Retrofit**: Considera **SCT-013** (clamp-on)
4. **Per DC/Precision**: Usa **INA226**

### Next Steps:

- [ ] Testa ACS712 con setup attuale
- [ ] Ordina PZEM-004T per test
- [ ] Implementa baseline learning
- [ ] Aggiungi dashboard power metrics
- [ ] Integra alert su anomalie corrente

**Vuoi che implementi il driver PZEM-004T completo nel progetto?**
