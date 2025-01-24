# Telegram-Posts lesen


Von Channeln kann man Posts auf zwei Arten lesen: 

- über ihre Kontextseite (t.me/s/<channel>/<id>)
- über ihre individuelle Post-Seite (t.me/s/<channel>/<id>)

## Kontextseite


Die Kontextseite ist etwas bequemer, denn: 
- sie lädt direkt komplett (die Post-Seite lädt ein Embed nach)
- sie wird auch angezeigt, wenn es die Post-ID nicht gibt


## Postseite


Die Postseite lädt die eigentlichen Inhalte als Embed in ein iframe. Es ist möglich, dieses Embed direkt über requests zu laden: 
- https://t.me/<channel>/<id>?embed=1&mode=tme
  - Parameter embed: alles >0 scheint zu funktionieren
  - Parameter mode: akzeptiert auch andere Namen
- Untersuchen, ob es ein Element div.tgme_widget_message_error enthält - dann konnte der Post nicht geladen werden
- Enthält ein Element div.tgme_widget_message_error

<div class="tgme_widget_message text_not_supported_wrap js-widget_message" data-post="telegram/361" data-view="eyJjIjotMTAwNTY0MDg5MiwicCI6MzYxLCJ0IjoxNzM1OTQxNTY5LCJoIjoiOGJmNWMzZDM1OTE0Y2I1NTMyIn0" data-peer="c1005640892_-6044378432856379164" data-peer-hash="556f33b85ddb50a1e1" data-post-id="361">

# Funktionen in der Library:

## tgc_clean(cname:str) -> str

Bin mir gar nicht sicher, dass das immer nötig ist; als ich 2018 mit R eine erste Telegram-Library geschrieben
habe, war die Funktion Standard bei mir - es wird Gründe gegeben haben. Schaden tut's nicht. 

* **cname**: Telegram-Kanal-Name, z.B. "FragUnsDochDasOriginal"
* **Rückgabewert**: Der geputzte Namens-String ohne unzulässige Zeichen 


## tgc_profile(channel: str) -> dict

Liest die Rahmendaten eines Channels aus der Profil-Karte und gibt sie als Dict zurück. 

* **channel**: Telegram-Kanal-Name (str), z.B. "Telegram"
* **Rückgabewert**: ein dict mit den Keys
  * 'channel': str, name des Kanals
  * 'description': str, Beschreibung des Kanals
  * 'image_url' und 'image': str und base64-str; das Profilbild
  * 'subscribers': int Anzahl Abonnenten
  * 'photos': int, Anzahl veröffentlichter Fotos
  * 'videos': int, Anzahl veröffentlichter Videos
  * 'links': int, Anzahl veröffentlichter LInks
  * 'n_posts' int, Nummer des letzten publizierten Posts
  
n_posts entspricht streng genommen nicht ganz der Anzahl der veröffentlichten Posts, weil diese Zahl insbesondere zu Beginn eines Kanals springen kann. 

## tgc_read, tgc_blockread etc. 

Auslesen von Telegram-Posts über die Kontext- bzw. Post-Seite. 

Alle Read-Funktionen nutzen intern eine Funktion namens tgc_post_parse, die aus einem HTML-Objekt die Daten extrahiert und geben deshalb im wesentlichen alle dasselbe zurück: eine Liste von dict-Einträgen (für jeden Posts) mit folgenden Keys: 

  * 'channel': str, Kanalname
  * 'nr': int, Nummer des Posts
  * 'url': str, URL des Posts (so wie man sie durch Klick auf den Zeitstempel bekommt)
  * 'views': int, Anzahl der Abrufe des Posts (laut Telegram - Vorsicht!)
  * 'views_ts': str, Zeitpunkt des Views-Abrufs in Iso-Format
  * 'timedate': str, Zeitstempel des Posts im ISO-Format
  * 'text': str, Text des Posts (falls vorhanden, sonst None)
  * 'photo': dict, gepostetes Bild bzw. Vorschaubild bei Videos (falls vorhanden, sonst None)
    * 'url': str, Link auf Photo-Datei (könne evtl. nicht stabil sein!)
    * 'image': str, base64 des Bildes
    * 'description': str, KI-Inhaltsbeschreibung des Bildes (nur falls bestellt, sonst kein Key)
    * 'file': str, Dateiname des gesicherten Medieninhalts. (nur falls save=True, sonst kein Key)
  * 'sticker': sticker,
    * 'url': str, Link auf Sticker-Image-Datei (könne evtl. nicht stabil sein!)
    * 'image': str, base64 des Bildes
    * 'description': str, KI-Inhaltsbeschreibung des Bildes (nur falls describe=True, sonst kein Key)
    * 'file': str, Dateiname des gesicherten Medieninhalts. (nur falls save=True, sonst kein Key)
  * 'video': video,
    * 'url': str, Link auf Photo-Datei (könne evtl. nicht stabil sein!)
    * 'image': str, base64 des Bildes
    * 'description': str, KI-Inhaltsbeschreibung des Bildes (nur falls describe=True, sonst kein Key)
    * 'file': str, Dateiname des gesicherten Medieninhalts. (nur falls save=True, sonst kein Key)
  * 'voice': dict, Sprachnachricht, falls vorhanden
    * 'url': str, Link auf Photo-Datei (könne evtl. nicht stabil sein!)
    * 'duration': str, base64 des Bildes
    * 'transcription': str, KI-Transkription des Audios (nur falls describe=True, sonst kein Key)
    * 'file': str, Dateiname des gesicherten Medieninhalts (nur falls save=True, sonst kein Key) 
  * 'forwards': forward,
    * 'url': str, Link zum Quell-Posts
    * 'name': str, Name des Quell-Kanals
  * 'poll': str, Umfrage-Typ (bekannt: 'anonymous') 
  * 'links': Liste der Link-Strings
  * 'hashtags': Liste der Hashtag-Strings, [f"#{tag}" for tag in hashtags],

### tgc_read(cname, nr, save=True, describe = False) -> dict
Liest einzelnen Post aus dem angegebenen Kanal mit der angegebenen Nr. über Post-Seite Ruft ```tgc_read_url``` auf.
### tgc_read_url(url, save=True, describe = False) -> dict
Liest einzelnen Post über Post-Seiten-Link.
### tgc_blockread(cname="telegram", nr=None, save=True, describe=False) -> [dict]

Ruft eine Kontext-Seite zentriert auf den Post ```nr``` auf. (wie t.me/s/<kanalname>/<nr>) - Die Kontext-Seite zeigt bis zu 16 Posts und zentriert i.d.R. auf den gegebenen Post.

### tgc_read_range(cname, n1=1, n2=None, save=True, describe = True) -> [dict]
Liest die Posts von n1 bis n2

### tgc_read_number(cname, n = 20, cutoff = None, save=True, describe = True)
Beginnt beim Post mit der Nummer ```cutoff``` und versucht dann ```n``` Posts zu lesen.

## Auswertungs-Funktionen: 

Zunächst hatte ich alles seriell abgearbeitet: Posts einlesen, mit KI verschriftlichen, ggf.
die Tonspur eines Videos/eine Voice-Message in mp3 wandeln, mit KI-Checker prüfen. Das dauerte
zu lange, um brauchbar zu sein, deshalb ist der Prozess in zwei Schritte aufgeteilt, die sich
(einigermaßen) parallelisieren lassen: 

tg_hydrate(posts) -> [dict]
* **posts**: Eine Liste von dicts (Format siehe oben: tgc_read...)

Liest die Mediendateien von Fotos, Stickern, Videos und Voice-Nachrichten in den ```/media```-Ordner
im Arbeitsverzeichnis. Anfragen werden asynchron gestellt, also parallelisiert; dadurch geht's recht flott. 

Gibt das posts-Dict mit den Dateinamen der heruntergeladenen Mediendateien zurück. 

tg_evaluate(posts, check_texts=True, check_media=True) -> [dict]
* **posts**: Eine Liste von hydrierten dicts (Format siehe oben: tgc_read...)
* **check_media**: Bilder, Videos und Voice auf KI-Spuren checken

Erledigt parallel alles mit KI: Beschreibung, KI-Check bei Text, Bild und Ton. 
Da AIORNOT nur MP3-Dateien sauber verarbeiten kann, ist bei Videos/Voice-Nachrichten eine
Wandlung aus MP4 bzw. OGG vorgeschaltet; das passiert mithilfe von ffmpeg - und nicht asynchron.
Da Telegram-Dateien in der Regel klein sind, ist der Zeitaufwand aber zu verschmerzen. 

Setzt ein hydriertes posts-Dict voraus (sonst passiert wenig); gibt den Posts die Keys 
```detectora_ai_score``` (KI-Texterkennungs-Vertraunswert, ein Wert zwischen 0 und 1) und 
```aiornot_ai_score``` zurück. 

```aiornot_ai_score``` ist ein dict aus: 

* score: 'ai' oder 'human'
* confidence: Vertrauenswert der KI-Erkennung (leider nicht bei Video/Voice, deshalb gibt die Routine den unsinnigen Wert 1.01 zurück)
* generator: ein dict, das für die bekannten KI-Bildgeneratoren jeweils einen Key enthält, in dem ein Dict mit dem 'confidence'-Wert für den einzelnen Generator gespeichert ist. Der Eintrag mit dem höchsten confidence-Wert war's wahrscheinlich (allerdings wird z.B. Flux als DALLE erkannt.)