# VibraSense Cloud Integration Guide

## 🌐 Overview

Il Raspberry Pi può inviare dati al cloud usando **HTTP POST** o **MQTT**. Per default usa HTTP perché più semplice e compatibile con Cloudflare Workers.

---

## 🚀 Quick Start (HTTP Mode)

### **1. Configurazione**

Modifica `config/config.json`:

```json
{
  "transmission": {
    "mode": "http",
    "http_url": "https://your-worker.workers.dev",
    "http_timeout": 10
  },
  "device": {
    "device_id": "rpi-001",
    "machine_id": 1,
    "company_id": 1
  }
}
```

### **2. Test Connessione**

```bash
# Test del cloud worker
curl https://your-worker.workers.dev/api/ingest/health

# Output atteso:
# {"status":"healthy","service":"VibraSense MQTT Ingestion","timestamp":"2026-05-01T..."}
```

### **3. Avvio Servizio**

```bash
cd ~/rpi-edge-client
git pull origin main
sudo systemctl restart vibrasense-edge
sudo journalctl -u vibrasense-edge -f
```

### **4. Verifica Trasmissione**

Cerca nei log:

```
✓ HTTP client connected: https://your-worker.workers.dev
✓ Readings transmitted (6 sensors)
✓ Readings published successfully: 18 sensors
```

---

## 📊 Formato Dati

### **Input dal Raspberry Pi (sensor_manager)**

```json
{
  "timestamp": 1714579200.0,
  "machine_id": 1,
  "company_id": 1,
  "readings": [
    {
      "sensor_id": 1,
      "sensor_name": "Vibrazioni Mandrino",
      "type": "vibration",
      "data": {
        "accel_x": 0.05,
        "accel_y": 0.03,
        "accel_z": 1.01,
        "gyro_x": 2.3,
        "gyro_y": -1.2,
        "gyro_z": 0.8
      }
    },
    {
      "sensor_id": 3,
      "type": "temperature",
      "data": {
        "temperature": 31.5
      }
    },
    {
      "sensor_id": 5,
      "type": "current",
      "data": {
        "current": 11.2,
        "voltage": 1.68
      }
    }
  ]
}
```

### **Output verso Cloud Worker**

```json
{
  "timestamp": "2026-05-01T17:00:00.000Z",
  "machine_id": 1,
  "company_id": 1,
  "readings": [
    {
      "sensor_id": 1,
      "type": "vibration",
      "value_rms": 0.05,
      "unit": "g",
      "axis": "x"
    },
    {
      "sensor_id": 1,
      "type": "vibration",
      "value_rms": 0.03,
      "unit": "g",
      "axis": "y"
    },
    {
      "sensor_id": 1,
      "type": "vibration",
      "value_rms": 1.01,
      "unit": "g",
      "axis": "z"
    },
    {
      "sensor_id": 101,
      "type": "gyroscope",
      "value_rms": 2.3,
      "unit": "dps",
      "axis": "x"
    },
    {
      "sensor_id": 3,
      "type": "temperature",
      "value": 31.5,
      "unit": "celsius"
    },
    {
      "sensor_id": 5,
      "type": "current",
      "value_rms": 11.2,
      "unit": "ampere"
    },
    {
      "sensor_id": 205,
      "type": "voltage",
      "value": 1.68,
      "unit": "volt"
    }
  ],
  "device_info": {
    "device_id": "rpi-001"
  }
}
```

---

## 🔧 Troubleshooting

### **Errore: HTTP connection test failed**

```bash
# 1. Verifica che il worker sia raggiungibile
curl https://your-worker.workers.dev/api/ingest/health

# 2. Verifica connessione internet del Pi
ping -c 3 8.8.8.8

# 3. Controlla firewall
sudo iptables -L -n
```

### **Errore: HTTP POST failed: 400 - Validation error**

Il payload non rispetta lo schema. Controlla i log:

```bash
sudo journalctl -u vibrasense-edge -n 100
```

### **Errore: database is locked**

SQLite in uso da altro processo:

```bash
# Riavvia il servizio
sudo systemctl restart vibrasense-edge

# Verifica che non ci siano altre istanze
ps aux | grep python3 | grep main.py
```

---

## 🔄 Switch tra HTTP e MQTT

### **Modalità HTTP (Default)**

```json
{
  "transmission": {
    "mode": "http",
    "http_url": "https://your-worker.workers.dev"
  }
}
```

### **Modalità MQTT**

```json
{
  "transmission": {
    "mode": "mqtt",
    "mqtt_enabled": true
  }
}
```

Poi configura `config/mqtt.json`:

```json
{
  "broker": {
    "host": "your-mqtt-broker.com",
    "port": 8883,
    "username": "vibrasense",
    "password": "your-password"
  }
}
```

---

## 📈 Monitoraggio

### **Log in tempo reale**

```bash
sudo journalctl -u vibrasense-edge -f
```

### **Ultime 100 righe**

```bash
sudo journalctl -u vibrasense-edge -n 100
```

### **Filtra solo successi**

```bash
sudo journalctl -u vibrasense-edge | grep "Readings transmitted"
```

### **Filtra solo errori**

```bash
sudo journalctl -u vibrasense-edge | grep ERROR
```

---

## 🎯 Testing

### **Test Locale (senza cloud)**

```bash
cd ~/rpi-edge-client
source venv/bin/activate
python3 -c "
from src.http_client import HTTPClient
client = HTTPClient(
    base_url='https://3000-io7myyqug4gr4l7itchut-c81df28e.sandbox.novita.ai',
    machine_id=1,
    company_id=1
)
print('Connection:', client.connect())
"
```

### **Test End-to-End**

```bash
# 1. Sul Raspberry Pi, forza una lettura
sudo systemctl restart vibrasense-edge

# 2. Sul cloud, verifica arrivo dati
curl https://your-worker.workers.dev/api/readings/latest?machine_id=1
```

---

## 📚 Riferimenti

- **HTTPClient**: `src/http_client.py`
- **Main Application**: `src/main.py`
- **Configuration**: `config/config.json`
- **Cloud Worker Docs**: (link al repo del worker)
