# 📱 Guida Setup WiFi - VibraSense Edge Client

## Per l'Utente Finale (Cliente/Tecnico)

---

## 🎯 Cosa Serve

- ✅ Raspberry Pi VibraSense (già configurato)
- ✅ Alimentatore 5V 3A
- ✅ Smartphone o tablet
- ✅ Credenziali WiFi dell'officina (nome rete + password)

**Tempo richiesto**: 5 minuti

---

## 📋 Procedura Passo-Passo

### Passo 1: Alimentazione

```
🔌 Collega l'alimentatore al Raspberry Pi
⏳ Attendi 60 secondi per l'avvio completo
📡 Il LED WiFi lampeggerà (indica hotspot attivo)
```

### Passo 2: Connessione Smartphone

```
📱 Apri le impostazioni WiFi del tuo smartphone

🔍 Cerca reti WiFi disponibili

📶 Troverai una rete chiamata:
   "VibraSense-Setup-XXX"
   (dove XXX è il numero macchina)

🔐 Tocca la rete e inserisci la password:
   vibrasense2026

✅ Attendi la connessione (5-10 secondi)
```

### Passo 3: Configurazione Automatica

```
🌐 Il browser si aprirà automaticamente
   (se non si apre, vai a: http://10.3.141.1)

📋 Vedrai la pagina "VibraSense - Configurazione WiFi"

🔘 Clicca su "Configura WiFi"

⌨️  Inserisci:
   • Nome rete WiFi officina
   • Password WiFi

💾 Clicca "Salva e Connetti"
```

### Passo 4: Connessione Completata

```
⏳ "Connessione in corso..." (30-60 secondi)

✅ "Connesso! Sistema pronto"

📡 Il LED WiFi diventa fisso (verde)

🚀 Il sistema è operativo e trasmette dati
```

---

## 🎨 Screenshot Processo

### 1. Lista Reti WiFi
```
┌─────────────────────────────┐
│     Scegli una rete         │
├─────────────────────────────┤
│ WiFi Casa                   │
│ VibraSense-Setup-001  📡   │ ← Questa!
│ TIM-12345678                │
│ Vodafone-AB12CD             │
└─────────────────────────────┘
```

### 2. Inserisci Password Hotspot
```
┌─────────────────────────────┐
│   VibraSense-Setup-001      │
├─────────────────────────────┤
│ Password:                   │
│ ┌─────────────────────────┐ │
│ │ vibrasense2026 ········ │ │
│ └─────────────────────────┘ │
│         [Connetti]          │
└─────────────────────────────┘
```

### 3. Pagina Configurazione
```
┌─────────────────────────────┐
│        📡 VibraSense        │
│   Configurazione WiFi       │
├─────────────────────────────┤
│ Nome rete WiFi officina:    │
│ ┌─────────────────────────┐ │
│ │ WiFi-Officina           │ │
│ └─────────────────────────┘ │
│                             │
│ Password:                   │
│ ┌─────────────────────────┐ │
│ │ ··················      │ │
│ └─────────────────────────┘ │
│                             │
│    [Salva e Connetti] →     │
└─────────────────────────────┘
```

---

## 🔧 Risoluzione Problemi

### ❌ Non vedo la rete "VibraSense-Setup-XXX"

**Soluzione**:
1. Verifica che il Raspberry Pi sia acceso (LED verde fisso)
2. Attendi 2 minuti dall'accensione
3. Avvicina lo smartphone al Raspberry Pi
4. Riavvia il Raspberry Pi se necessario (scollega/ricollega alimentatore)

---

### ❌ Password hotspot errata

**Soluzione**:
- La password predefinita è: **vibrasense2026** (tutto minuscolo)
- Se modificata, controlla l'etichetta sul dispositivo

---

### ❌ Browser non si apre automaticamente

**Soluzione**:
1. Apri il browser manualmente
2. Vai all'indirizzo: **http://10.3.141.1**
3. Se non funziona, disconnetti e riconnetti al WiFi hotspot

---

### ❌ "Connessione fallita" dopo aver inserito credenziali WiFi

**Cause possibili**:
1. **Password WiFi errata**: Controlla maiuscole/minuscole
2. **WiFi fuori portata**: Avvicina il Raspberry Pi al router
3. **WiFi 5GHz**: Raspberry Pi 4 supporta solo 2.4GHz + 5GHz, verifica compatibilità

**Soluzione**:
- Il sistema torna automaticamente in modalità hotspot dopo 5 minuti
- Riprova la configurazione con credenziali corrette

---

### ❌ LED WiFi lampeggia continuamente

**Significato**: Dispositivo in modalità hotspot (non connesso a WiFi)

**Soluzione**:
- Normale durante prima configurazione
- Se persiste dopo configurazione → verifica credenziali WiFi

---

## 📞 Supporto

### Assistenza Tecnica
- 📧 Email: support@vibrasense.io
- 📱 Telefono: +39 XXX XXX XXXX
- 🌐 Documentazione: https://docs.vibrasense.io

### Prima di contattare il supporto
Prepara queste informazioni:
- Numero seriale dispositivo (etichetta sul Raspberry Pi)
- Descrizione problema
- Foto LED (se possibile)

---

## 📊 Indicatori LED

| LED | Stato | Significato |
|-----|-------|-------------|
| 🟢 Fisso | Connesso | WiFi OK, sistema operativo |
| 🟡 Lampeggiante | Hotspot | In attesa configurazione |
| 🔴 Fisso | Errore | Problema sistema |
| ⚫ Spento | Off | Nessuna alimentazione |

---

## ✅ Checklist Post-Installazione

Dopo aver completato il setup WiFi:

- [ ] LED verde fisso
- [ ] Smartphone può disconnettersi dall'hotspot VibraSense
- [ ] Dispositivo visibile su dashboard cloud (entro 5 minuti)
- [ ] Sensori trasmettono dati regolarmente

Se tutto è ✅, l'installazione è completa!

---

## 🔄 Resettare Configurazione WiFi

Se devi cambiare la rete WiFi:

**Metodo 1: Da Dashboard Cloud**
1. Accedi alla dashboard VibraSense
2. Seleziona la macchina
3. Vai su "Impostazioni → WiFi"
4. Clicca "Riconfigura WiFi"
5. Il dispositivo tornerà in modalità hotspot

**Metodo 2: Manualmente (accesso fisico)**
1. Scollega alimentazione Raspberry Pi
2. Attendi 10 secondi
3. Tieni premuto il pulsante reset (se presente)
4. Ricollega alimentazione mentre tieni premuto
5. Rilascia dopo 5 secondi
6. Il dispositivo tornerà in modalità hotspot

---

## 📦 Contenuto Confezione

Verifica di avere tutto:

- [ ] Raspberry Pi VibraSense (con case)
- [ ] Alimentatore 5V 3A
- [ ] Cavo USB-C/Micro-USB
- [ ] Sensori industriali (se applicabile)
- [ ] Cavi connessione sensori
- [ ] Etichetta con credenziali hotspot
- [ ] Questa guida stampata

---

## 🎓 Video Tutorial

Scansiona il QR code per vedere il video tutorial:

```
┌─────────────────┐
│  █▀▀▀▀▀█ █▄ █  │
│  █ ███ █  ▀▀▄█ │
│  █ ▀▀▀ █ ▀█ ▀█ │
│  ▀▀▀▀▀▀▀ █ ▀ █ │
│  █▀▀▀▀▀█ ▄  ▄█ │
│  ▀▀▀▀▀▀▀ ▀▀▀▀▀ │
└─────────────────┘
```

O visita: **https://www.vibrasense.io/setup**

---

**Buon monitoraggio con VibraSense!** 🚀
