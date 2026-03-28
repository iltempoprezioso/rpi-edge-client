# 📝 Guida Configurazione VibraSense Edge Client

## 🎯 File di Configurazione

Il sistema utilizza 3 file di configurazione nella directory `config/`:

| File | Obbligatorio | Contiene | Esempio |
|------|--------------|----------|---------|
| `config.json` | ⚠️ Raccomandato | Device ID, Company ID, percorsi buffer/log | `config.example.json` |
| `mqtt.json` | ⚠️ Raccomandato | Credenziali broker MQTT | `mqtt.example.json` |
| `sensors.json` | ✅ Versionato | Configurazione sensori hardware | *(già pronto)* |

---

## 🚀 Auto-Fallback Intelligente

### ✨ Novità: Sistema Tollerante agli Errori

Il client **NON si blocca** se mancano `config.json` o `mqtt.json`. Invece:

1. **Cerca il file principale** (`config.json`)
2. **Se mancante**, carica automaticamente il file `.example` corrispondente
3. **Mostra un warning** nei log per ricordarti di configurarlo
4. **Continua l'avvio** con valori di esempio funzionanti

### 📋 Comportamento Dettagliato

#### Caso 1: File `config.json` Mancante

```bash
# Log output:
WARNING - config.json not found, using config.example.json
WARNING - ⚠️  IMPORTANT: Copy config.example.json to config.json and configure device_id, company_id
INFO - Configuration loaded from config.example.json
```

**Cosa succede**:
- ✅ Sistema **parte comunque**
- ⚠️ Usa device_id generico (`rpi-001`)
- ⚠️ Usa company_id di test (`1`)
- ⚠️ **Dati pubblicati su topic MQTT errati** (company_id sbagliato)

**Azione richiesta**:
```bash
cp config/config.example.json config/config.json
nano config/config.json  # Modifica device_id, company_id
sudo systemctl restart vibrasense-edge
```

---

#### Caso 2: File `mqtt.json` Mancante

```bash
# Log output:
WARNING - mqtt.json not found, using mqtt.example.json
WARNING - ⚠️  IMPORTANT: Copy mqtt.example.json to mqtt.json and configure broker credentials
INFO - MQTT client initialized with config from mqtt.example.json
WARNING - MQTT connection failed, will retry in background
```

**Cosa succede**:
- ✅ Sistema **parte comunque**
- ⚠️ Usa broker di test (`test.mosquitto.org`)
- ⚠️ Usa credenziali di esempio (`username: machine_001`, `password: CHANGE_ME_SECRET_TOKEN`)
- ⚠️ **Connessione MQTT fallisce** (credenziali errate)
- ✅ Dati **bufferizzati localmente** in SQLite
- 🔄 Sistema **riprova connessione** in background ogni 5 secondi

**Azione richiesta**:
```bash
cp config/mqtt.example.json config/mqtt.json
nano config/mqtt.json  # Modifica host, username, password
sudo systemctl restart vibrasense-edge
```

---

## ⚙️ Configurazione Passo-Passo

### 1️⃣ Installazione Iniziale

```bash
cd /home/pi/rpi-edge-client

# Crea i file di configurazione dai template
cp config/config.example.json config/config.json
cp config/mqtt.example.json config/mqtt.json
```

### 2️⃣ Configura Device ID

Modifica `config/config.json`:

```json
{
  "device": {
    "device_id": "M001",           // ← Cambia con ID univoco macchina
    "machine_id": 1,               // ← ID numerico macchina
    "company_id": 123,             // ← ID cliente VibraSense
    "machine_name": "CNC Principale",
    "location": "Reparto A - Linea 1"
  },
  "acquisition": {
    "read_interval": 30,           // ✅ 30 secondi (GIÀ CORRETTO)
    "enabled": true,
    "auto_start": true,
    "max_retry_on_error": 5
  }
  // ... resto immutato ...
}
```

### 3️⃣ Configura Credenziali MQTT

Modifica `config/mqtt.json`:

```json
{
  "broker": {
    "host": "mqtt.vibrasense.io",  // ← Broker produzione
    "port": 8883,
    "use_tls": true,
    "protocol": "mqttv311"
  },
  "credentials": {
    "username": "device_M001",     // ← Username fornito da VibraSense
    "password": "TOKEN_SEGRETO"    // ← Password fornita da VibraSense
  },
  "tls": {
    "ca_cert": "/etc/vibrasense/ca.crt",      // ← Certificato CA (se richiesto)
    "client_cert": null,                       // ← null se non serve autenticazione certificati
    "client_key": null,
    "insecure": false
  }
  // ... resto immutato ...
}
```

### 4️⃣ Verifica Configurazione

```bash
# Test sensori
source venv/bin/activate
python3 tests/test_real_sensors.py

# Avvia servizio
sudo systemctl start vibrasense-edge

# Monitora logs
sudo journalctl -u vibrasense-edge -f

# Verifica che NON ci siano warning "using .example"
# Output atteso:
# INFO - Configuration loaded from config.json        ✅
# INFO - MQTT client initialized with config from mqtt.json  ✅
# INFO - Connected to MQTT broker mqtt.vibrasense.io:8883    ✅
```

---

## 🔧 Configurazione Sensori

### ✅ `sensors.json` è Già Pronto!

Il file `config/sensors.json` è **versionato** e contiene la configurazione **corretta** per il tuo hardware:

```json
{
  "sensors": [
    {
      "driver": "ism330dhcx",      // ✅ Hardware reale
      "address": "0x6A",            // ✅ I2C address corretto
      "enabled": true
    },
    {
      "driver": "max6675",          // ✅ Hardware reale
      "cs_pin": 0,                  // ✅ SPI CE0
      "enabled": true
    },
    {
      "driver": "sct013_ads1115",   // ✅ Hardware reale
      "address": "0x48",            // ✅ I2C address ADS1115
      "enabled": true
    }
  ],
  "acquisition": {
    "read_interval": 30,            // ✅ 30 secondi
    "burst_interval": 300,          // ✅ FFT ogni 5 minuti
    "burst_mode_enabled": true,     // ✅ FFT attivo
    "burst_trigger": "timer"
  }
}
```

**⚠️ NON modificare `sensors.json`** a meno che tu non cambi l'hardware fisico.

---

## 🐛 Risoluzione Problemi

### Problema: "Configuration file not found"

**Causa**: Mancano sia `config.json` CHE `config.example.json`

**Soluzione**:
```bash
cd /home/pi/rpi-edge-client
git pull origin main  # Scarica file .example
cp config/config.example.json config/config.json
```

### Problema: "MQTT connection failed"

**Causa**: Credenziali MQTT errate in `mqtt.json`

**Verifica**:
```bash
cat config/mqtt.json | grep -E "host|username|password"
```

**Soluzione**:
```bash
nano config/mqtt.json  # Correggi host, username, password
sudo systemctl restart vibrasense-edge
```

### Problema: Warning "using mqtt.example.json" nei log

**Causa**: File `mqtt.json` non esiste

**Soluzione**:
```bash
cp config/mqtt.example.json config/mqtt.json
nano config/mqtt.json  # Configura credenziali
sudo systemctl restart vibrasense-edge
```

### Problema: Dati non arrivano al cloud

**Causa 1**: Device ID errato in `config.json`
```bash
grep device_id config/config.json
# Verifica che corrisponda a quello registrato su VibraSense Cloud
```

**Causa 2**: Company ID errato in `config.json`
```bash
grep company_id config/config.json
# Verifica con il team VibraSense
```

**Causa 3**: Topic MQTT errati
```bash
# Verifica topic nei logs:
sudo journalctl -u vibrasense-edge | grep "Publishing to topic"
# Deve essere: vibrasense/{company_id}/machine/{machine_id}/readings
```

---

## 📊 Valori Predefiniti (Fallback)

### In `main.py` (linea 79-102)

| Configurazione | Valore Predefinito |
|----------------|-------------------|
| Config file fallback | `config.example.json` |
| MQTT config fallback | `mqtt.example.json` |

### In `sensor_manager.py` (linea 236)

| Parametro | Valore Predefinito |
|-----------|-------------------|
| `read_interval` | **30 secondi** ✅ (era 600) |

---

## ✅ Checklist Configurazione Completa

Usa questa checklist per verificare che tutto sia configurato correttamente:

- [ ] File `config.json` esiste (non usa `.example`)
- [ ] `device_id` univoco configurato
- [ ] `machine_id` corretto
- [ ] `company_id` corretto (fornito da VibraSense)
- [ ] File `mqtt.json` esiste (non usa `.example`)
- [ ] `host` broker MQTT corretto (`mqtt.vibrasense.io`)
- [ ] `username` e `password` MQTT corretti
- [ ] File `sensors.json` esiste (versionato, già pronto)
- [ ] Test hardware passa: `python3 tests/test_real_sensors.py`
- [ ] Servizio avviato: `sudo systemctl status vibrasense-edge`
- [ ] Logs NON mostrano warning ".example"
- [ ] MQTT connesso: logs mostrano "Connected to MQTT broker"
- [ ] Dati pubblicati ogni 30 secondi: logs mostrano "Publishing to topic"

---

## 🎯 Risultato Finale

Con questa configurazione il sistema:

✅ **Funziona immediatamente** anche senza config.json/mqtt.json (usa `.example`)  
✅ **Mostra warning chiari** se usa valori di esempio  
✅ **Non si blocca mai** durante l'avvio  
✅ **Bufferizza dati localmente** se MQTT non connesso  
✅ **Riprova connessione MQTT** automaticamente in background  
✅ **Legge sensori ogni 30 secondi** (fallback corretto)  
✅ **FFT attivo a 6660 Hz** ogni 5 minuti  

**Sistema production-ready con graceful degradation! 🚀**

---

**Repository**: https://github.com/iltempoprezioso/rpi-edge-client  
**Documentazione**: `README.md`, `PRODUCTION_CONFIG_FIX.md`, `CODE_REVIEW_FIXES.md`
