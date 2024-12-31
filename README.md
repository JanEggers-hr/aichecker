# aichecker
Checks Bluesky accounts (and, later, similar media) for AI suspicion. 

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
- Programm im Verzeichnis starten mit ```python check_bsky_profile.py````

Programm ist voreingestellt auf 20 Posts. (Sonst die Variable limit in Zeile 15 von check_bsky_profile.py ändern.) Die Schwelle für einen "echten" KI-Text-Post ist auf 80% (0.8) eingestellt. 

Das Skript legt im Verzeichnis ```bsky-checks``` eine CSV-Datei mit der Analyse nach Posts an, mit dem Namen des Profils: {handle}.CSV

## Achtung!

- Die Detectora-API setzt ein älteres Modell ein, das die GPT4-Erkennung nicht so gut schafft.
- AIORNOT ist teuer! Standardmodell: 100 API-Calls pro Monat für 5$ (bei Abschluss Jahresabo)
- Immer dran denken: Die Detektoren liefern Wahrscheinlichkeiten, keine Gewissheiten. 
