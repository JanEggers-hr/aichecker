# check_tt.py
#
# TikTok-Profile und -posts auslesen und auf KI prüfen
# Nutzt einen über RAPIDAPI.com eingekauften und eingebundenen Scraper:
# https://rapidapi.com/tikwm-tikwm-default/api/tiktok-scraper7/
#
# 2-2025 Manuel Paas

import pandas as pd
import requests
from datetime import datetime
import http.client
import json
import os
import re
import base64
import logging

# Funktionen in der aichecker-Library
from .transcribe import gpt4_description, transcribe, convert_mp4_to_mp3, convert_ogg_to_mp3
from .check_wrappers import detectora_wrapper, aiornot_wrapper, transcribe_async, describe_async, detectora_async, aiornot_async, hive_visual, hive_visual_async
from .save_urls import save_url_async, save_url
from .hydrate import hydrate_async
from .evaluate import evaluate_async

# Sonstige Bibliotheken
from ast import literal_eval # Strings in Objekte konvertieren
import asyncio # Asynchrone Funktionen
import aiohttp
from typing import List, Dict, Any, Optional # Typisierung für besseres Handling der Libraries

#################################
# BLOCK 1: Profil-Informationen #
#################################

def ttc_profile(username="mrbeast"):
    """
    Generiert Basisstatistiken für ein TikTok-Profil.

    Parameter:
    username (str)

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
            
    Beispiel: 
    profile = ttc_profile("mrbeast")
    profile = ttc_profile("nonexistentuser") # gibt None zurück
    """

    conn = http.client.HTTPSConnection("tiktok-scraper7.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': os.getenv('RAPIDAPI_KEY'),
        'x-rapidapi-host': "tiktok-scraper7.p.rapidapi.com"
    }

    try:
        conn.request("GET", f"/user/info?unique_id={username}", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8")).get('data', {})
    except Exception as e:
        logging.warning(f"Warnung: Benutzer {username} nicht gefunden. Fehler: {e}")
        return None

    if not data:
        return None

    profile_info = {
        'id': data.get('id'),
        'uniqueId': data.get('uniqueId'),
        'nickname': data.get('nickname'),
        'avatarThumb': data.get('avatarThumb'),
        'avatarMedium': data.get('avatarMedium'),
        'avatarLarger': data.get('avatarLarger'),
        'signature': data.get('signature'),
        'verified': data.get('verified'),
        'secUid': data.get('secUid'),
        'secret': data.get('secret'),
        'ftc': data.get('ftc'),
        'relation': data.get('relation'),
        'openFavorite': data.get('openFavorite'),
        'commentSetting': data.get('commentSetting'),
        'duetSetting': data.get('duetSetting'),
        'stitchSetting': data.get('stitchSetting'),
        'privateAccount': data.get('privateAccount'),
        'isADVirtual': data.get('isADVirtual'),
        'isUnderAge18': data.get('isUnderAge18'),
        'ins_id': data.get('ins_id'),
        'twitter_id': data.get('twitter_id'),
        'youtube_channel_title': data.get('youtube_channel_title'),
        'youtube_channel_id': data.get('youtube_channel_id')
    }

    return profile_info


def ttc_clean(cname):
    """
    Hilfsfunktion, die einen bereinigten TikTok-Namen in Kleinbuchstaben zurückgibt.

    Parameter:
        cname (str): TikTok-Name oder URL.

    Rückgabe:
    str: Kleinbuchstaben des extrahierten TikTok-Namens.
    """
    # In Kleinbuchstaben umwandeln
    name = cname.lower()
    
    # Regex-Muster definieren
    patterns = [
        r"(?<=tiktok\.com/@)[a-zäöüß0-9_\.]+",
        r"(?<=www\.tiktok\.com/@)[a-zäöüß0-9_\.]+",
        r"(?<=http://tiktok\.com/@)[a-zäöüß0-9_\.]+",
        r"(?<=https://tiktok\.com/@)[a-zäöüß0-9_\.]+",
        r"(?<=http://www\.tiktok\.com/@)[a-zäöüß0-9_\.]+",
        r"(?<=https://www\.tiktok\.com/@)[a-zäöüß0-9_\.]+",
        r"(?<=@)[a-zäöüß0-9_\.]+",
        r"^[a-zäöüß0-9_\.]+$"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            return match.group(0)
    
    return None

##################################################
# BLOCK 2: Posts auslesen und parsen #
##################################################

def ttc_post_parse(tiktok_data, save=False, describe=False):
    """ ttc_post_parse - Verarbeitet die TikTok-Daten von der RapidAPI und analysiert die Medien.

    Args:
        tiktok_data ([dict]): eine Liste von Diktaten  
        save (bool, optional): Medien auf die Festplatte speichern. Standard ist False.
        describe (bool, optional): Medien beschreiben/transkribieren. Standard ist False. NB: describe beinhaltet save!

    Returns:
        List von Diktaten: 
            'id': Video-ID
            'timestamp': Erstellungszeitpunkt,
            'query_ts': Abfrage-Timestamp (um Veränderungen bei den Likes tracken zu können)
            'text': Titel des Videos
            'likes': Anzahl der Likes, int
            'comment_count': Anzahl der Kommentare, int
            'share_count': Anzahl der Shares, int
            'type': immer 'video'
            'media': eine Liste von Diktaten mit Elementen: {
                'type': 'video', 
                'url': Video-URL, 
                'file': lokale Datei, falls gespeichert
                'transcription': falls describe gesetzt wurde
            }
            'location': Standortinformationen als Diktat, falls vorhanden
            
    """
    posts = []
    for item in tiktok_data:
        query_ts = datetime.now().isoformat()
        # Extrahiere Videodetails
        video_id = str(item.get('aweme_id', None))
        timestamp = datetime.fromtimestamp(item.get('create_time', 0)).isoformat()
        title = item.get('title', None)
        likes = item.get('digg_count', 0)
        comment_count = item.get('comment_count', 0)
        share_count = item.get('share_count', 0)
        
        # Extrahiere Mediendetails
        media = []
        if 'play' in item:
            media.append({'type': 'video', 'url': item['play']})
        
        # Extrahiere Standortinformationen
        location = None
        if 'anchors' in item and item['anchors']:
            try:
                location_extra = json.loads(item['anchors'][0].get('extra', '{}'))
                location = {
                    'name': location_extra.get('Name', None),
                    'city_code': location_extra.get('city_code', None),
                    'region_code': location_extra.get('region_code', None),
                    'formatted_address': location_extra.get('formatted_address', None)
                }
            except json.JSONDecodeError:
                location = None
        
        # Speichere Medien, falls erforderlich
        if save or describe:
            for i in range(len(media)):
                media_type = media[i]['type']
                media_url = media[i]['url']
                media[i]['file'] = save_url(media_url, f"{video_id}_{media_type}_{i}")
        
        # Beschreibe Medien, falls erforderlich
        if describe:
            for i in range(len(media)):
                media_file = media[i]['file']
                media[i]['transcription'] = transcribe(media_file)
        
        post_dict = {
            'id': video_id,
            'timestamp': timestamp,
            'text': title,
            'likes': likes,
            'comment_count': comment_count,
            'share_count': share_count,
            'type': 'video',
            'media': media,
            'location': location
        }
        
        posts.append(post_dict)
    
    return posts

def ttc_read_posts_until(cname, cutoff="1970-01-01T00:00:00", save=False, describe=False):
    """ Liest ein TikTok-Profil aus, bis das Cutoff-Datum erreicht ist oder nix mehr da.

    Args:
        cname (str): Name des Profils
        save (bool, optional): Medien abspeichern. Legacy. Defaults to False.
        describe (bool, optional): Medien beschreiben/transkribieren. Legacy. Defaults to False.

    Returns:
        Liste der Posts
    """

    conn = http.client.HTTPSConnection("tiktok-scraper7.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': os.getenv('RAPIDAPI_KEY'),
        'x-rapidapi-host': "tiktok-scraper7.p.rapidapi.com"
    }

    posts = []
    cursor = "0"
    read_on = True
    while read_on:
        conn.request("GET", f"/user/posts?unique_id={cname}&count=30&cursor={cursor}", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        cursor = data.get('cursor', "")
        
        if data.get('code') != 0:
            e = data.get('msg', 'Unbekannter Fehler')
            print(f"TikTok-API-Fehler: {e}")
            logging.error(f"TikTok-API-Fehler: {e}")
            return None
        
        # Frühesten gelesenen Zeitstempel ermitteln
        try:
            min_ts = min(d['create_time'] for d in data['data']['videos'])
        except ValueError as e:
            logging.error(f"TikTok-API-Fehler: Keine Daten? {e}")
            logging.error(f"data['data']['videos']")
            return None
        
        if min_ts <= cutoff:
            read_on = False
            new_posts = [d for d in data['data']['videos'] if d['create_time'] > cutoff]
            posts.extend(new_posts)
        else:
            posts.extend(data['data']['videos'])

        if not data.get('hasMore', False):
            break

    # Die Posts parsen und die URLS der Videos und Fotos extrahieren
    return ttc_post_parse(posts, save=save, describe=describe)

def ttc_read_posts(cname, n=12, save=False, describe=False):
    """ Liest die n letzten Posts eines TikTok Profils aus.

    Args:
        cname (str): Name des Profils
        save (bool, optional): Medien abspeichern. Legacy. Defaults to False.
        describe (bool, optional): Medien beschreiben/transkribieren. Legacy. Defaults to False.

    Returns:
        siehe oben ttc_post_parse
    """

    conn = http.client.HTTPSConnection("tiktok-scraper7.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': os.getenv('RAPIDAPI_KEY'),
        'x-rapidapi-host': "tiktok-scraper7.p.rapidapi.com"
    }

    posts = []
    cursor = "0"

    while len(posts) < n:
        conn.request("GET", f"/user/posts?unique_id={cname}&count=30&cursor={cursor}", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        cursor = data.get('cursor', "")
        
        if data.get('code') != 0:
            e = data.get('msg', 'Unbekannter Fehler')
            print(f"TikTok-API-Fehler: {e}")
            logging.error(f"TikTok-API-Fehler: {e}")
            return []

        posts.extend(data['data']['videos'])

        if not data.get('hasMore', False):
            break

    # Die Posts parsen und die URLS der Videos und Fotos extrahieren
    return ttc_post_parse(posts, save=save, describe=describe)


# API unterstützt weder Stories, noch Bilder-Gallery-Beiträge #

########################################
### Block 3: Hydrieren und auswerten ###
########################################

def tt_hydrate(posts, mdir="./media"):
    return asyncio.run(hydrate_async(posts, mdir))

def tt_evaluate(posts: List[Dict[str, Any]], check_texts: bool = True, check_images: bool = True) -> List[Dict[str, Any]]:
    return asyncio.run(evaluate_async(posts, check_texts=check_texts, check_images=check_images))

## Routinen zum Check der letzten 20(...) Posts eines Telegram-Channels
# analog zu check_handle in der check_bsky-Library
#
# Hinter den Kulissen werden Listen von Post-dicts genutzt



#### Handling der CSV

# Hilfsfunktion: CSV einlesen und als df ausgeben
# Benötigt "from ast import literal_eval" 
def convert_to_obj(val):
    if pd.isna(val):
        return None
    try:
        return literal_eval(val)  # Funktion aus der Bibliothek ast
    except (ValueError, SyntaxError):
        return val

# Hilfsfunktion: CSV einlesen und als DataFrame ausgeben
def tt_reimport_csv(fname):
    df = pd.read_csv(fname)
    # Diese Spalten sind dicts:
    structured_columns = ['media', 'location']
    for c in structured_columns:
        if c in df.columns:
            df[c] = df[c].apply(convert_to_obj)
    return df

def tt_append_csv(tiktok_name, posts_list, path="tt-checks"):
    filename = f'{path}/{tiktok_name}.csv'
    if os.path.exists(filename):
        existing_df = tt_reimport_csv(filename)
    else:
        existing_df = pd.DataFrame()
    df = pd.DataFrame(posts_list)
    if existing_df is not None:
        df = pd.concat([existing_df, df]).drop_duplicates(subset=['id']).reset_index(drop=True)
    df.to_csv(filename, index=False)

