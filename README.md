# aichecker
Bluesky-Konten und Telegram channels auf KI-Inhalte-Verdacht abprüfen. 

## Wozu es gut ist

Das Fernziel ist eine Recherche zu KI-Inhalten im Wahlkampf mit zwei Stoßrichtungen:

- Verdachtsfälle besonders krasser Fälschungen finden
- Gesamt-KI-Anteil nach Partei/Person

## Wie einsetzen?


- Mit ```git clone github.com/JanEggers-hr/aichecker``` in ein Verzeichnis klonen
- In dem Verzeichnis eine ```.env``` Datei anlegen mit den Keys: 
```
OPENAI_API_KEY="" # für die Bildbeschreibungen
DETECTORA_API_KEY="" # für die Textanalyse
AIORNOT_API_KEY="" # für die Bildanalyse
```
- Programm im Verzeichnis starten mit ```python main_ig.py``` bzw. ```python main_tg.py``` (noch veraltet: ```python main_bsky.py```)


Programm ist voreingestellt auf 20 Posts. (Sonst die Variable limit in Zeile 15 von check_bsky_profile.py ändern.) Die Schwelle für einen "echten" KI-Text-Post ist auf 80% (0.8) eingestellt. 

Das Skript legt im Verzeichnis ```bsky-checks``` bzw. ```tg-checks```eine CSV-Datei mit der Analyse nach Posts an, mit dem Namen des Profils: {handle}.CSV . - Mediendateien werden unter ```media``` abgelegt. 

## Für Cronjobs: ```ig_scraper.py````

Die Datei ist dafür ausgerichtet, in der Kommandozeile zu laufen, gesteuert durch ein Google-Sheet, und die Ergebnisdateien so zu speichern, dass man über eine Verlinkung im Google-Sheet rankommt. 

Sie sammelt neben neuen Posts auch Stories und Highlights, weshalb es LANGE dauern kann, bis es durchgelaufen ist. 

###  Parameter
* --channel:    Instagram-Handle 
* --channels:   Komma-separierte Liste von Instagram-Handles
* --gsheet:     Google-Sheet-ID (z.B. 1Tr1YU8zVu7AFBWy8HS9ZWVxFUgQPc51rvf-UlrXRXXM)
* --jsonpath:   Pfad zur JSON-Datei mit den Google-API-Schlüsseln (z.B. /Users/janeggers/Code/aichecker/credentials.json)
* --savepath:   Pfad zum Speichern der Dateien (z.B. /Users/janeggers/Code/aichecker/bsky-checks)
* --serverpath: Server-Adresse, unter der die Assets nacher abrufbar sind Server (z.B. "https://frankruft.de/ig-checks)

Die JSON-Datei erzeugt man in der [Google-Cloud-Konsole](https://console.cloud.google.com/), dort muss man ein "Helper-Account" anlegen (das Zugriff auf das Google-Sheet braucht) und dann die JSON-Datei herunterladen.

### Wrapper-Skript

...dafür ausgelegt, mit dem Apache-Default-User www-data ausgeführt zu werden. Es muss drei Dinge tun, damit es funktioniert: 
- das Python-Environment aktivieren (am besten das für die Dash-Umgebung)
- den .env File übergeben
- das Skript starten

``` bash
#!/bin/bash

# Activate the virtual environment
source /path/to/env/dash/bin/activate

# Source environment variables if needed
source /path/to/home/demos/.env

# Run your Python script
/path/to/env/dash/bin/python /path/to/scripts/aichecker/ig_scraper.py --gsheet asdfasdfasdf --savepath /path/to/save --serverpath https://frankruft.de/ig-checks --json /path/to/home/demos/credentials.json
```
Dies Skript kann mit den www-data Cronjobs aufgerufen werden; die bearbeitet man mit: 

```
sudo crontab -u www-data -e
```

Zu Testzwecken auf der Kommandozeile mit Rechten von www-data aufrufen: 
```
sudo -u www-data /path/to/wrapper.sh
# alternativ: Task mit nohup starten, um ausloggen zu können
sudo -u www-data /path/to/wrapper.sh nohup /path/to/python/ig_scan_wrapper.sh > /path/to/python/ig_scan_logfile.log 2>&1 &
```


### Google-Sheet
 channels |	start_scan |	msg	xlsx |	posts |	media |	last_post |	ai_text |	 |ai_image |	ai_video |	ai_audio |
 |---|---|---|---|---|---|---|---|---|---|---|

## Verwendung als Python-Library

Direkt aus dem Repository installieren: 
* pip install git+https://github.com/JanEggers-hr/aichecker.git -U
* pip install git+ssh://git@github.com/JanEggers-hr/aichecker.git -U

```import aichecker```

## Achtung!

- Die Detectora-API setzt ein älteres Modell ein, das die GPT4-Erkennung nicht so gut schafft.
- AIORNOT ist sehr begrenzt! Standardmodell: 100 API-Calls pro Monat für 5$ (bei Abschluss Jahresabo). Über Enterprise-Zugang gibt es kein Limit mehr, da kosten 10000 Calls 500$ (und darüber hinaus 4 Cent).
- Immer dran denken: Die Detektoren liefern Wahrscheinlichkeiten, keine Gewissheiten. 

