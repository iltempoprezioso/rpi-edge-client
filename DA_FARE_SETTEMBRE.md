# Da fare quando i pod saranno montati sul tornio (settembre 2026)

## 1. Tarare la soglia di corrente del mandrino  [IMPORTANTE]

Il campo `machine_state` (idle/running) serve a etichettare i dati per il
machine learning. Ora la soglia e' **0.5 A: un valore PROVVISORIO, inventato**.
Va sostituito con quello vero, misurato sul tornio.

**Come fare:**

1. Tornio spento -> guarda la corrente letta:
   `sudo journalctl -u vibrasense-edge -f | grep "Sensor 5"`
2. Mandrino acceso a vuoto (non taglia) -> guarda la corrente
3. Mandrino in lavorazione -> guarda la corrente
4. Metti la soglia **a meta' tra fermo e rotazione a vuoto** in
   `config/sensors.json` -> `acquisition.spindle_current_threshold_a`
5. Riavvia: `sudo systemctl restart vibrasense-edge`
6. Verifica che `machine_state` cambi davvero da idle a running

**Perche' e' importante:** se la soglia e' sbagliata, tutti i dati sono
etichettati male e il modello ML impara una baseline senza senso.

## 2. Misurare la temperatura del cuscinetto mandrino  [DECIDE ACQUISTI]

Durante un ciclo di lavorazione VERO (non a vuoto), misurare la temperatura
massima raggiunta dal supporto cuscinetto.

- MAX6675 e' rated **0-70 C**
- Magneti al neodimio standard reggono **~80 C**

Se si superano i **60-70 C** servono:
- MAX31855 al posto del MAX6675
- magneti grado H o SH (alta temperatura)

**Non comprare prima di aver misurato.**

## 3. Dati reali della macchina  [SOGLIE ISO]

Nel database ci sono dati inventati da Genspark: "Haas VF-2", power_kw 15.
La **classe ISO 10816 dipende dalla potenza della macchina**, quindi le soglie
di severita' (zone A/B/C/D) sono tarate su una macchina che non esiste.

Da aggiornare con: potenza reale, modello, tipo di montaggio (rigido/elastico).

## 4. Sicurezza meccanica  [PRIMA DI ACCENDERE]

- **Tether di sicurezza obbligatorio** sui pod magnetici vicino al mandrino
- Verificare che il supporto sia in acciaio (l'alluminio non tiene il magnete)

## 5. Prima di installare presso terzi  [BLOCCANTE]

- **Conferma scritta** che la polizza RC della SRL copre prodotti di terzi e
  il servizio di monitoraggio, incluso il progettista
- Consenso firmato per prototipo R&D (unita' gratuite = esenzione marcatura CE)
