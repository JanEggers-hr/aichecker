# Instagram-Posts lesen

Basis-Code von Manuel Paas: https://github.com/manuelpaas/

Nutzt eine von [rapidapi.com](hptts://rapidapi.com) bereitgestellte API: https://rapidapi.com/social-api1-instagram/api/instagram-scraper-api2. 

## Struktur

Die Bibliothek orientiert sich stark an den Telegram-Funktionen; sie teilt sich grob auf in:

- Funktion zum Auslesen eines Profils
- Funktionen zum Auslesen und Parsen von einzelnen Posts
- Funktionen zum Herunterladen ("Hydrieren") und Analysieren der Medien

## Profil auslesen

def igc_profile(username="mrbeast") -> dict:


Generates base statistics for an Instagram profile.

Parameters:
* username (str)

Returns:
        dict with the keys 
- 'username'
- 'biography'
- 'country'
- 'profile_pic_url' (high resolution)
- 'external_url'
- 'full_name'
- 'is_private' (boolean)
- 'is_verified' (boolean)
- 'following_count' (Number)
- 'follower_count' (Number)
- 'media_count' (number)
- 'created' (isoformat string with datetime)

Example: 
```
profile = igc_profile("mrbeast")
profile = igc_profile("nonexistentuser") # returns None
```

## Posts auslesen

Liest die letzten n Posts eines Profils aus. (Default: 12)

def igc_read_posts(username="mrbeast", n=12) -> list:

Gibt ein List of dict zurück: 
- 'id': post id (URL ist: https://www.instagram.com/p/{id}/)
- 'timestamp': timestamp,
- 'caption': caption, text
- 'hashtags': a list of hashtags
- 'mentions': a list of mentions
- 'location': location as a dict containing the address (or None if none is given)
    - 'id': INstagram/Facebook-Location-ID
    - 'name': Instagram-Ortsbezeichnung,
    - 'street_address': Straße
    - 'zip_code': Postleitzahl
    - 'city_name': Stadt('city_name', None),
    - 'region_name': Bundesland etc.
    - 'country_code': US, DE etc. 
- 'likes': number of likes, int
- 'comment_count': number of comments, int
- 'type': 'video', 'image' oder 'carousel'
- 'media': Eine Liste von dicts für jedes Element: 
	- 'type': video, image 
	- 'url': URL des Elements (temporär)
	- Hier werden dann später auch die 'file' und 'description'/'transcription' Keys eingetragen.


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

tg_hydrate(posts, mdir = "./media") -> [dict]
* **posts**: Eine Liste von dicts (Format siehe oben: tgc_read...)
* **mdir**: Das Verzeichnis für Mediendateien - auf dem Server funktioniert "./media" allerdings nicht; da am besten den kompletten Pfad angeben 

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