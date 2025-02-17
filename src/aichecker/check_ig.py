# check_ig.py
#
# Instagram-Profile und -posts auslesen und auf KI prüfen
# Nutzt einen über RAPIDAPI.com eingekauften und eingebundenen Scraper:
# https://rapidapi.com/social-api1-instagram/api/instagram-scraper-api2
#
# 2-2025 Jan Eggers, Basiscode von Manuel Paas https://github.com/manuelpaas

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

def igc_profile(username="mrbeast"):
    """
    Generates base statistics for an Instagram profile.

    Parameters:
    username (str)

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
    - 'query_ts': Abfrage-Timestamp (um Veränderungen bei den Likes tracken zu können)
            
    
    Example: 
    profile = igc_profile("mrbeast")
    profile = igc_profile("nonexistentuser") # returns None
    """

    conn = http.client.HTTPSConnection("instagram-scraper-api2.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': os.getenv('RAPIDAPI_KEY'),
        'x-rapidapi-host': "instagram-scraper-api2.p.rapidapi.com"
    }
    logging.info(f"Queriying profile for {username} with API key {headers['x-rapidapi-key'][:5]}...")

    try:
        conn.request("GET", f"/v1/info?username_or_id_or_url={username}&include_about=true", headers=headers)
        res = conn.getresponse()
        logging.info(f"RAPID API returning status {res.status}")
        data = json.loads(res.read().decode("utf-8")).get('data', {})
        query_ts = datetime.now().isoformat()
    except Exception as e:
        logging.warning(f"Warning: User {username} not found. Error: {e}")
        return None

    if not data:
        return None
    
    # Timestamp is Unix timestamp, convert to datetime
    joined_raw = data.get('about', {}).get('date_joined_as_timestamp')
    joined_datetime = datetime.fromtimestamp(joined_raw) if joined_raw else None
    joined = joined_datetime.isoformat() if joined_datetime else None

    profile_info = {
        'username': data.get('username'),
        'biography': data.get('biography'),
        'country': data.get('about',{}).get('country'),
        'profile_pic_url': data.get('profile_pic_url_hd'),
        'external_url': data.get('external_url'),
        'full_name': data.get('full_name'),
        'is_private': data.get('is_private'),
        'is_verified': data.get('is_verified'),
        'following_count': data.get('following_count'),
        'follower_count': data.get('follower_count'),
        'media_count': data.get('media_count'),
        'created': joined,
        'query_ts': query_ts
    }

    return profile_info


def igc_clean(cname):
    """
    Hilfsfunktion, die einen bereinigten Instagram-Namen in Kleinbuchstaben zurückgibt.

    Parameter:
        cname (str): Instagram-Name oder URL.

    Rückgabe:
    str: Kleinbuchstaben des extrahierten Instagram-Namens.
    """
    # In Kleinbuchstaben umwandeln
    name = cname.lower()
    
    # Regex-Muster definieren
    patterns = [
        r"(?<=instagram\.com/)[a-zäöüß0-9_\.]+",
        r"(?<=www\.instagram\.com/)[a-zäöüß0-9_\.]+",
        r"(?<=http://instagram\.com/)[a-zäöüß0-9_\.]+",
        r"(?<=https://instagram\.com/)[a-zäöüß0-9_\.]+",
        r"(?<=http://www\.instagram\.com/)[a-zäöüß0-9_\.]+",
        r"(?<=https://www\.instagram\.com/)[a-zäöüß0-9_\.]+",
        r"(?<=@)[a-zäöüß0-9_\.]+",
        r"^[a-zäöüß0-9_\.]+$"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            return match.group(0)
    
    return None

##################################################
# BLOCK 2: Posts und Stories auslesen und parsen #
##################################################

def ig_post_parse(instagram_data, save=False, describe=False):
    """ ig_post_parse - Takes rapidapi instagram data output and parses the media.

    Args:
        instagram_data ([dict]): a list of dicts  
        save (bool, optional): save media to disk. Defaults to False.
        describe (bool, optional): describe/transcribe media. Defaults to False. NB: describe includes save!

    Returns:
        List of dict: 
            'id': post id (URL ist: https://www.instagram.com/p/{id}/)
            'timestamp': timestamp,
            'query_ts': Abfrage-Timestamp (um Veränderungen bei den Likes tracken zu können)
            'text': caption, text
            'hashtags': a list of hashtags
            'mentions': a list of mentions
            'location': location as a dict containing the address (or None if none is given)#
                'id' : location id
                'name': location name
                'street_address': location.get('address_json', {}).get('street_address', None),
                'zip_code': location.get('address_json', {}).get('zip_code', None),
                'city_name': location.get('address_json', {}).get('city_name', None),
                'region_name': location.get('address_json', {}).get('region_name', None),
                'country_code': US, DE etc.
            ' 
            'likes': number of likes, int
            'comment_count': number of comments, int
            'type': one in ['image', 'video', 'carousel']
            'media': a list of dicts containing elements: {
                'type': ('video', 'image'), 
                'url': url, 
                'file': local file if saved
                'description' / 'transcription': just that if describe was set
            
    """
    posts = []
    for item in instagram_data:
        query_ts = datetime.now().isoformat()
        # Extract post details
        post_code = str(item.get('id', None))
        timestamp = datetime.fromtimestamp(item.get('taken_at_ts', 0)).isoformat()
        if item.get('caption') is None:
            item.pop('caption')
            caption = None
        else: 
            caption = item.get('caption', {}).get('text', None)
        hashtags = item.get('caption', {}).get('hashtags', [])
        mentions = item.get('caption', {}).get('mentions', [])
        location = item.get('location', None)
        if location:
            location = {
                'id' : location.get('id', None),
                'name': location.get('name', None),
                'street_address': location.get('address_json', {}).get('street_address', None),
                'zip_code': location.get('address_json', {}).get('zip_code', None),
                'city_name': location.get('address_json', {}).get('city_name', None),
                'region_name': location.get('address_json', {}).get('region_name', None),
                'country_code': location.get('address_json', {}).get('country_code', None),
                
            }
        else:
            location = None
        
        # Extract media details
        media = []
        
        # Check for carousel media
        # Kann Image und Video gemischt enthalten
        if 'carousel_media' in item:
            type = 'carousel'
            for i in item['carousel_media']:
                if 'image_versions' in i:
                    # Erstes Bild ist die Originalversion, das reicht
                    # media.append({'type': 'image', 'url': i['image_versions']['items'][0]['url']})
                    # Bringt aber AIORNOT durcheinander, deshalb das zweite
                    try:
                        media.append({'type': 'image', 'url': i['image_versions']['items'][1]['url']})
                    except:
                        media.append({'type': 'image', 'url': i['image_versions']['items'][0]['url']})
                    
                if 'video_url' in i:
                    media.append({'type': 'video', 'url': i['video_url']})
        else:
            # Single image or video
            
            if 'video_url' in item:
                media.append({'type': 'video', 'url': item['video_url']})
                type = 'video'
            else: 
                type = 'image'
                if 'image_versions' in item:
                # Erstes Bild ist die Originalversion
                # Zweites Bild ist etwas kleliner
                    try: 
                        media.append({'type': 'image', 'url': item['image_versions']['items'][1]['url']})
                    except:
                        media.append({'type': 'image', 'url': i['image_versions']['items'][0]['url']})

        
        # Construct post dictionary
        
        # Save media if required
        if save or describe:
            for i in range(len(media)):
                media_type = media[i]['type']
                media_url = media[i]['url']
                media[i]['file'] = save_url(media_url, f"{post_code}_{media_type}_{idx}")
        
        
        # Describe media if required
        if describe:
            for i in range(len(media)):
                media_type = media[i]['type']
                media_file = media[i]['file']
                if media_type == 'image':
                    image = base64.b64encode(open(media_file, 'rb').read()).decode('utf-8')
                    media[i]['description'] = gpt4_description(f"data:image/jpeg;base64, {image}")
                else:
                    media[i]['transcription'] = transcribe(media_file)
        
        post_dict = {
            'id': post_code,
            'timestamp': timestamp,
            'text': caption,
            'hashtags': hashtags,
            'mentions': mentions,
            'location': item.get('location', None),
            'likes': item.get('like_count', 0),
            'comment_count': item.get('comment_count', 0),
            'type': type,
            'media': media
        }
        
        posts.append(post_dict)
    
    return posts

def igc_read_posts_until(cname, cutoff="1970-01-00T00:00:00", save=False, describe=False):
    """ Liest ein Insta-Profil aus, bis das Cutoff-Datum erreicht ist oder nix mehr da.

    Args:
        cname (str): Name des Profils
        n (int, optional): Anzahl der Posts. Defaults to 12.
        save (bool, optional): Medien abspeichern. Legacy. Defaults to False.
        describe (bool, optional): Medien beschreiben/transkribieren. Legacy. Defaults to False.

    Returns:
        siehe oben igc_parse_posts
    """

    conn = http.client.HTTPSConnection("instagram-scraper-api2.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': os.getenv('RAPIDAPI_KEY'),
        'x-rapidapi-host': "instagram-scraper-api2.p.rapidapi.com"
    }

    posts = []
    pagination_token = ""
    read_on = True
    # Konvertiere in Unix-Timestamp
    cutoff_unix = datetime.strptime(cutoff, "%Y-%m-%dT%H:%M:%S").timestamp()
    while read_on:
        if pagination_token == "":
            conn.request("GET", f"/v1.2/posts?username_or_id_or_url={cname}", headers=headers)
        else: 
            conn.request("GET", f"/v1.2/posts?username_or_id_or_url={cname}&pagination_token={pagination_token}", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        pagination_token = data.get('pagination_token', "")
        # Fehler werden als Key "detail" zurückgegeben
        if 'detail' in data:
            e = data.get('detail')
            print(f"Instagram-API-Fehler: {e}")
            logging.error(f"Instagram-API-Fehler: {e}")
            return None
        
        # Frühesten gelesenen Zeitstempel ermitteln
        try:
            min_ts = min(d['taken_at_ts'] for d in data['data']['items'])
            # Konvertiere min_ts in datetime isoformat
            
        except ValueError as e:
            logging.error(f"Instagram-API-Fehler: Keine Daten? {e}")
            logging.error(f"data['data']['items']")
        if min_ts <= cutoff_unix:
            read_on = False
            new_posts = [d for d in data['data']['items'] if d['taken_at_ts'] > cutoff_unix]
            posts.extend(new_posts)
        else:
            posts.extend(data['data']['items'])

        if not pagination_token:
            break

    # Die Posts parsen und die URLS der Videos und Fotos extrahieren
    return ig_post_parse(posts, save=save, describe=describe)

def igc_read_posts(cname, n=12, save=False, describe=False):
    """ Liest die n letzten Posts eines Instagram Profils aus.

    Args:
        cname (str): Name des Profils
        cutoff (str, optional): Datetime-isoformat-String mit dem Datum, bei dem aufgehört werden soll 
        save (bool, optional): Medien abspeichern. Legacy. Defaults to False.
        describe (bool, optional): Medien beschreiben/transkribieren. Legacy. Defaults to False.

    Returns:
        siehe oben igc_parse_posts
    """

    conn = http.client.HTTPSConnection("instagram-scraper-api2.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': os.getenv('RAPIDAPI_KEY'),
        'x-rapidapi-host': "instagram-scraper-api2.p.rapidapi.com"
    }

    posts = []
    pagination_token = ""

    while len(posts) < n:
        if pagination_token == "":
            conn.request("GET", f"/v1.2/posts?username_or_id_or_url={cname}", headers=headers)
        else: 
            conn.request("GET", f"/v1.2/posts?username_or_id_or_url={cname}&pagination_token={pagination_token}", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        pagination_token = data.get('pagination_token', "")
        # Fehler werden als Key "detail" zurückgegeben
        if 'detail' in data:
            e = data.get('detail')
            print(f"Instagram-API-Fehler: {e}")
            logging.error(f"Instagram-API-Fehler: {e}")
            return []
        if 'message' in data:
            e = data.get('message')
            print(f"Instagram-API-Fehler: {e}")
            logging.error(f"Instagram-API-Fehler: {e}")
            return []

        posts.extend(data['data']['items'])

        if not pagination_token:
            break

    # Die Posts parsen und die URLS der Videos und Fotos extrahieren
    return ig_post_parse(posts, save=save, describe=describe)


def igc_read_stories(cname, save=False, describe=False):
    """ Liest die sichtbaren Stories aus. Zwingt sie in die gleiche Logik wie Posts. 
    Stories kriegen den Typ 'story'
    D.h.: Videos und Images werden unter "media" als einziger Eintrag in einer Liste gespeichert.
    
    Args:
        cname (str): der Name des Profils
        save (bool): ob die Medien gespeichert werden sollen
        describe (bool): ob die Medien beschrieben werden sollen

    Ausgabe: siehe oben igc_parse_posts
    """
    
    conn = http.client.HTTPSConnection("instagram-scraper-api2.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': os.getenv('RAPIDAPI_KEY'),
        'x-rapidapi-host': "instagram-scraper-api2.p.rapidapi.com"
    }

    conn.request("GET", f"/v1/stories?username_or_id_or_url={cname}", headers=headers)
    res = conn.getresponse()
    data = json.loads(res.read().decode("utf-8"))
    # Fehler werden als Key "detail" zurückgegeben
    if 'detail' in data:
        e = data.get('detail')
        print(f"Instagram-API-Fehler Stories: {e}")
        logging.error(f"Instagram-API-Fehler Stories: {e}")
        return []
    if 'message' in data:
        e = data.get('message')
        print(f"Instagram-API-Message Stories: {e}")
        logging.error(f"Instagram-API-Message Stories: {e}")
        return []

    posts = data['data']['items']
    parsed_posts =[]
    # Stories parsen: (Wissensstand: 3.2.2025)
    # Es gibt grundsätzlich zwei Arten von Stories, Video-Stories und Bilderstories.
    # - Bilder-Stories: Eine Liste von Bild-Urls in 
    # - Video-Stories: URL des Videos in ['video_url']
    for post in posts:
        print(".",end="")
        parsed_post = {
            'id': post['id'],
            'timestamp': datetime.fromtimestamp(post['taken_at']).isoformat(), # Highlights haben nur ein Unix-TS in created_at
            'text': post.get('caption',''),
            'type': 'story ',
            'hashtags': [],
            'mentions': [],
            'location': None,
        }
        # Mentions im Key: reel_mentions (haben nur Videos?)
        mentions_raw = post.get('reel_mentions',[])
        parsed_post['mentions'] = [{'username': mention['user']['username']} for mention in mentions_raw]
        if 'video_url' in post:
            parsed_post['media'] = [{'type': 'video', 'url': post['video_url']}]
        elif 'image_versions' in post:
            image = post['image_versions'].get('items',[])[1]
            if image is not None:
                parsed_post['media'] = [{'type': 'image', 'url': image.get('url')}]
            # Mentions im Key: 
        parsed_posts.append(parsed_post)
    return parsed_posts


def igc_read_highlights(cname, save=False, describe=False):
    """ Liest die sichtbaren Highlights aus (die Stories, die im Profil angepinnt sind). 
    Zwingt sie in die gleiche Logik wie Posts. Highlights kriegen den Typ 'highlight' 
    D.h.: Videos und Images werden unter "media" als einziger Eintrag in einer Liste gespeichert.
    
    ANSCHEINEND ENTHALTEN HIGHLIGHTS ABER SELBER KEINE MEDIEN
    
    Args:
        cname (str): der Name des Profils
        save (bool): ob die Medien gespeichert werden sollen
        describe (bool): ob die Medien beschrieben werden sollen

    Ausgabe: siehe oben igc_parse_posts
    """
    
    conn = http.client.HTTPSConnection("instagram-scraper-api2.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': os.getenv('RAPIDAPI_KEY'),
        'x-rapidapi-host': "instagram-scraper-api2.p.rapidapi.com"
    }

    conn.request("GET", f"/v1/highlights?username_or_id_or_url={cname}", headers=headers)
    res = conn.getresponse()
    data = json.loads(res.read().decode("utf-8"))
    # Fehler werden als Key "detail" zurückgegeben
    if 'detail' in data:
        e = data.get('detail')
        print(f"Instagram-API-Fehler Highlights: {e}")
        logging.error(f"Instagram-API-Fehler Highlights: {e}")
        return []
    if 'message' in data:
        e = data.get('message')
        print(f"Instagram-API-Message Highlights: {e}")
        logging.error(f"Instagram-API-Message Stories: {e}")
        return []

    highlights = data['data']['items']
    parsed_posts =[]
    
    # Highlights parsen: (Wissensstand: 3.2.2025)
    # Erst mal die Infos abrufen, um sie herunterladen zu können. 
    # Sind im Prinzip wie Stories, heißen aber anders. 
    for h in highlights:
        # Erst mal die Info über einen weiteren API-Call holen
        id = h['id'].split(':')[-1]
        title = h['title']
        conn.request("GET", f"/v1/highlight_info?highlight_id={id}", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        try:
            posts = data['data']['items']
        except KeyError as e:
            logging.error(f"Instagram-API-Message Stories: {e}")
            return []    
        # Fehler werden als Key "detail" zurückgegeben
        for post in posts:
            # timestamp
            print(".",end="")
            timestamp = datetime.fromtimestamp(post['taken_at']).isoformat()
            parsed_post = {
                'id': id,
                'timestamp': timestamp, 
                'text': title,
                'type': 'highlight',
                'hashtags': [],
                'mentions': [],
                'location': None, 
            }
            # Mentions im Key: reel_mentions (haben nur Videos?)
            mentions_raw = post.get('reel_mentions',[])
            parsed_post['mentions'] = [{'username': mention['user']['username']} for mention in mentions_raw]
            if 'video_url' in post:
                parsed_post['media'] = [{'type': 'video', 'url': post['video_url']}]
            elif 'image_versions' in post:
                image = post['image_versions'].get('items',[])[1]
                if image is not None:
                    parsed_post['media'] = [{'type': 'image', 'url': image.get('url')}]
                # Mentions im Key: 
            parsed_posts.append(parsed_post)
    return parsed_posts

########################################
### Block 3: Hydrieren und auswerten ###
########################################

def ig_hydrate(posts, mdir="./media"):
    return asyncio.run(hydrate_async(posts, mdir))

def ig_evaluate(posts: List[Dict[str, Any]], check_texts: bool = True, check_images: bool = True) -> List[Dict[str, Any]]:
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
        return literal_eval(val) # Funktion aus der Llibrary ast
    except (ValueError, SyntaxError):
        return val

# Hilfsfunktion: CSV einlesen und als df ausgeben
def ig_reimport_csv(fname):
    df = pd.read_csv(fname)
    # Diese Spalten sind dict:
    structured_columns = ['hashtags','mentions','media']
    for c in structured_columns:
        if c in df.columns:
            df[c] = df[c].apply(convert_to_obj)
    return df
    
    
def ig_append_csv(handle, posts_list, path = "ig-checks"):
    filename = f'{path}/{handle}.csv'
    if os.path.exists(filename):
        existing_df = ig_reimport_csv(filename)
    else:
        existing_df = pd.DataFrame()
    df = pd.DataFrame(posts_list)
    if existing_df is not None: 
        df = pd.concat([existing_df, df]).drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df.to_csv(filename, index=False)

