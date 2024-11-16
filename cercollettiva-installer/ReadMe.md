
# CerCollettiva - Installer

## Panoramica
Script di installazione automatizzata per CerCollettiva, software open-source per la gestione delle Comunità Energetiche Rinnovabili (CER).

## Requisiti
- Raspberry Pi (Zero W, 3, o 4) con Raspberry Pi OS
- Minimo 1GB di spazio libero
- Connessione Internet
- Privilegi sudo per l'utente pi

## Installazione Rapida

Clona il repository:
```bash
git clone https://github.com/andreabernardi/cercollettiva-installer.git
cd cercollettiva-installer
```

Rendi eseguibile lo script:
```bash
chmod +x install.sh
```

Avvia l'installazione:
```bash
./install.sh
```

## Funzionalità

- ✅ Rilevamento automatico del modello Raspberry Pi
- ✅ Ottimizzazioni specifiche per hardware
- ✅ Setup completo ambiente Django
- ✅ Configurazione Nginx e Gunicorn
- ✅ Sistema di monitoring integrato
- ✅ Backup automatici
- ✅ Gestione MQTT
- ✅ Logging avanzato
- ✅ Report dettagliati

## Struttura Directory Post-Installazione

```
/home/pi/cercollettiva/
├── app/                # Codice applicazione Django
├── venv/              # Ambiente virtuale Python
├── backups/           # Backup automatici
├── logs/              # File di log
├── media/             # File caricati dagli utenti
└── staticfiles/       # File statici
```

## Configurazione

L'installer può essere personalizzato modificando le variabili in `scripts/00-config.sh`:

- Porte (Nginx, Gunicorn)
- Parametri MQTT
- Soglie monitoraggio
- Ottimizzazioni hardware
- Schedule backup

## Monitoraggio

Il sistema include monitoraggio automatico di:
- Utilizzo CPU/RAM/Disco
- Temperatura CPU
- Stato servizi
- Connessione MQTT
- Performance applicazione

## Backup

- Backup automatici giornalieri alle 2:00 AM
- Rotazione automatica (mantiene ultimi 7 giorni)
- Backup manuale disponibile:
```bash
/home/pi/cercollettiva/app/backup.sh
```

## Troubleshooting

### Log di Sistema

Visualizza log di installazione:
```bash
cat /home/pi/cercollettiva/installation.log
```

Monitora log applicazione:
```bash
tail -f /home/pi/cercollettiva/logs/application.log
```

Monitora log sistema:
```bash
tail -f /home/pi/cercollettiva/logs/system.log
```

### Controllo Servizi

Status servizi:
```bash
sudo systemctl status nginx
sudo systemctl status gunicorn
sudo systemctl status supervisor
sudo systemctl status cercollettiva-monitor
```

Restart servizi:
```bash
sudo systemctl restart nginx
sudo systemctl restart gunicorn
```

### Problemi Comuni

1. **Errore 502 Bad Gateway**
   - Verifica stato Gunicorn
   - Controlla log Gunicorn in `/home/pi/cercollettiva/logs/`

2. **Errori MQTT**
   - Verifica credenziali in `.env`
   - Controlla connettività broker

3. **Problemi Permessi**
   - Esegui `sudo chown -R pi:www-data /home/pi/cercollettiva`
   - Verifica permessi directory media e static

## Aggiornamenti

Per aggiornare il sistema:
```bash
cd /home/pi/cercollettiva/app
git pull
source ../venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

## Supporto

- 📖 [Documentazione Completa](https://github.com/andreabernardi/cercollettiva/docs)
- 🐛 [Segnalazione Bug](https://github.com/andreabernardi/cercollettiva/issues)
- 💬 [Community Support](https://github.com/andreabernardi/cercollettiva/discussions)

## Contribuire

Siamo aperti a contributi! Per favore:
1. Fork del repository
2. Crea un branch per le tue modifiche
3. Invia una Pull Request

## Licenza

Questo progetto è rilasciato sotto licenza MIT.

## Autore

- Andrea Bernardi

## Credits

Ringraziamenti speciali a tutti i contributori del progetto CerCollettiva.

---
