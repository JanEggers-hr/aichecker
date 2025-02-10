# TikTok-Posts lesen

Basis-Code von Manuel Paas: https://github.com/manuelpaas/

Nutzt eine von [rapidapi.com](https://rapidapi.com) bereitgestellte API: https://rapidapi.com/tikwm-tikwm-default/api/tiktok-scraper7/

## Struktur

Die Bibliothek orientiert sich stark an den Telegram-Funktionen; sie teilt sich grob auf in:

- Funktion zum Auslesen eines Profils
- Funktionen zum Auslesen und Parsen von einzelnen Posts
- Funktionen zum Herunterladen ("Hydrieren") und Analysieren der Medien

## Profil auslesen

def ttc_profile(username="mrbeast") -> dict:

Generiert Basisstatistiken für ein TikTok-Profil.

Parameter:

- username (str)

Rückgabe:
dict mit den Schlüsseln

- 'id'
- 'uniqueId'
- 'nickname'
- 'avatarThumb'
- 'avatarMedium'
- 'avatarLarger'
- 'signature'
- 'verified'
- 'secUid'
- 'secret'
- 'ftc'
- 'relation'
- 'openFavorite'
- 'commentSetting'
- 'duetSetting'
- 'stitchSetting'
- 'privateAccount'
- 'isADVirtual'
- 'isUnderAge18'
- 'ins_id'
- 'twitter_id'
- 'youtube_channel_title'
- 'youtube_channel_id'

Example:

```
profile = igc_profile("mrbeast")
profile = igc_profile("nonexistentuser") # returns None
```

## Posts auslesen

Liest die letzten n Posts eines TikTok-Profils aus. (Default: 12)

def ttc_read_posts(cname="mrbeast", n=12, save=False, describe=False) -> list:

Gibt eine List of dict zurück:

- 'id': Video-ID
- 'timestamp': Erstellungszeitpunkt
- 'text': Titel des Videos
- 'likes': Anzahl der Likes, int
- 'comment_count': Anzahl der Kommentare, int
- 'share_count': Anzahl der Shares, int
- 'type': immer 'video'
- 'media': Eine Liste von dicts für jedes Element:
  - 'type': 'video'
  - 'url': URL des Videos
  - Hier werden dann später auch die 'file' und 'transcription' Keys eingetragen, falls save oder describe gesetzt ist.

## ttc_profile(username: str) -> dict

Liest die Rahmendaten eines TikTok-Profils aus und gibt sie als Dict zurück.

- **username**: TikTok-Benutzername (str), z.B. "mrbeast"
- **Rückgabewert**: ein dict mit den Schlüsseln
  - 'id': TikTok-ID
  - 'uniqueId': Eindeutige ID
  - 'nickname': Spitzname
  - 'avatarThumb', 'avatarMedium', 'avatarLarger': URLs zu den Avataren
  - 'signature': Profilbeschreibung
  - 'verified': Verifizierungsstatus
  - 'secUid', 'secret', 'ftc', 'relation', 'openFavorite', 'commentSetting', 'duetSetting', 'stitchSetting', 'privateAccount', 'isADVirtual', 'isUnderAge18': Weitere Profilinformationen
  - 'ins_id', 'twitter_id', 'youtube_channel_title', 'youtube_channel_id': Verknüpfte Social-Media-IDs

## ttc_read, ttc_read_posts_until etc.

Auslesen von TikTok-Posts über die API.

Alle Read-Funktionen nutzen intern eine Funktion namens ttc_post_parse, die aus den API-Daten die Informationen extrahiert und geben deshalb im Wesentlichen alle dasselbe zurück: eine Liste von Diktat-Einträgen (für jeden Post) mit folgenden Schlüsseln:

- 'id': Video-ID
- 'timestamp': Erstellungszeitpunkt
- 'text': Titel des Videos
- 'likes': Anzahl der Likes
- 'comment_count': Anzahl der Kommentare
- 'share_count': Anzahl der Shares
- 'type': 'video'
- 'media': Liste von Diktaten mit Video-Details
- 'location': Standortinformationen, falls vorhanden

### ttc_read_posts_until(cname, cutoff="1970-01-01T00:00:00", save=False, describe=False) -> list

Liest ein TikTok-Profil aus, bis das Cutoff-Datum erreicht ist oder keine weiteren Posts mehr vorhanden sind.

### ttc_read_posts(cname, n=12, save=False, describe=False) -> list

Liest die letzten n Posts eines TikTok-Profils aus.

## Auswertungs-Funktionen:

tt_hydrate(posts, mdir="./media") -> list

- **posts**: Eine Liste von dicts (Format siehe oben: ttc_read...)
- **mdir**: Das Verzeichnis für Mediendateien - auf dem Server funktioniert "./media" allerdings nicht; da am besten den kompletten Pfad angeben

Liest die Mediendateien von Videos in den `/media`-Ordner im Arbeitsverzeichnis. Anfragen werden asynchron gestellt, also parallelisiert; dadurch geht's recht flott.

Gibt das posts-Dict mit den Dateinamen der heruntergeladenen Mediendateien zurück.

tt_evaluate(posts, check_texts=True, check_images=True) -> list

- **posts**: Eine Liste von hydrierten Diktaten (Format siehe oben: ttc_read...)
- **check_images**: Videos auf KI-Spuren checken

Erledigt parallel alles mit KI: Beschreibung, KI-Check bei Text und Video. Da AIORNOT nur MP3-Dateien sauber verarbeiten kann, ist bei Videos eine Wandlung aus MP4 vorgeschaltet; das passiert mithilfe von ffmpeg - und nicht asynchron. Da TikTok-Dateien in der Regel klein sind, ist der Zeitaufwand aber zu verschmerzen.

Setzt ein hydriertes posts-Dict voraus (sonst passiert wenig); gibt den Posts die Keys `detectora_ai_score` (KI-Texterkennungs-Vertrauenswert, ein Wert zwischen 0 und 1) und `aiornot_ai_score` zurück.
