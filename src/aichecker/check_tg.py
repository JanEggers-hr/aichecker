# tg_check.py
#
# Mistral-Übersetzung aus R (mein altes Rtgchannels-Projekt V0.1.1)
# Angepasst auf Listen statt Dataframes
# In Maßen parallellisiert - Dateien werden asynchron gespeichert, 
# API-Abfragen bei OPENAI, AIORNOT und Detectora asynchron gestellt (was eine GROSSE
# Zeitersparnis bedeutet!)
#
# 1-2025 Jan Eggers


import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil.parser import isoparse
import os
import re
import base64
import logging
from .transcribe import convert_mp4_to_mp3, convert_ogg_to_mp3
from .check_wrappers import describe_async, transcribe_async, detectora_async, aiornot_async, hive_visual
from .save_urls import save_url_async
from .evaluate import evaluate_async
from .hydrate import hydrate_async
import aiohttp
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional
import ast

def extract_k(n_str: str):
    try: 
        # Zahlen wie '5.06K', '1K', '1.2M'
        n_f = float(re.sub(r'[KMB]$', lambda m: {'K': 'e+03', 'M': 'e+06', 'B': 'e+09'}[m.group()], n_str))
        return int(n_f)
    except:
        return None

def tgc_profile(channel="telegram"):
    """
    Generates base statistics for a Telegram channel.

    Parameters:
    channel (str)

    Returns:
    dict with the keys 
    - 'channel'
    - 'description'
    # - 'image' (base64 des Profilbilds) und 'image_url' (URL des Profilbilds)
    - 'subscribers' (Number)
    - 'photos' (number)
    - 'videos' (number)
    - 'links' (number)
    - 'n_posts' (number of the last published post)
    - 'created' (wann angelegt)

    Example:
    profile = tgc_profile("wilhelmkachel")
    profile = tgc_profile("asdfasdfasdf") #  returns None
    """
    c = tgc_clean(channel)
    c_url = f"https://t.me/s/{c}"
    logging.info(f"Lese Info aus Channel {c}")
    try:
        response = requests.get(c_url)
        response.raise_for_status()
        tgm = BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException:
        logging.warning(f"Warning: Channel {c} not found")
        return None
    # Kein Channel? Channel haben immer wenigstens einen Namen in der Infokarte
    if tgm.select_one("div.tgme_channel_info") is None:
        return None
    if tgm.select_one("div.tgme_channel_info_description") is not None:
        description = tgm.select_one("div.tgme_channel_info_description").get_text()
    else:
        description = None
    img = tgm.select_one("i.tgme_page_photo_image") 
    if img is not None:
        image_url = img.select_one("img")['src']
        image = base64.b64encode(requests.get(image_url).content).decode('utf-8')
    else: 
        image_url = None
        image = None
    channel_info = {'name': c,
                    'description': description,
                    'image_url': image_url,
                    'image': image,
                    }
    for info_counter in tgm.find_all('div', class_='tgme_channel_info_counter'):
        counter_value = info_counter.find('span', class_='counter_value').text.strip()
        counter_type = info_counter.find('span', class_='counter_type').text.strip()
        # Sonderbedingungen: nur 1 Link, nur 1 Foto, nur 1 Video? Umbenennen für Konsistenz
        if counter_type in ['photo', 'video', 'link', 'subscriber']:
            counter_type += "s"
        channel_info[counter_type] = extract_k(counter_value)

    # The last post is visible on this page. Gather its number and date.
    # Wenn das Konto noch nicht gepostet hat: Abbruch. 
    if tgm.select_one("div.tgme_widget_message") is None:
        channel_info['n_posts'] = 0
    else: 
        last_post_href = tgm.select('a.tgme_widget_message_date')[-1]['href']
        channel_info['n_posts'] = int(re.search(r'[0-9]+$', last_post_href).group())
    # Get founding date of account. 
    # Dafür die seite t.me/<cname>/1 aufrufen und nach tgme_widget_message_service_date suchen
    c_url = f"https://t.me/s/{c}/1"
    try:
        response = requests.get(c_url)
        response.raise_for_status()
        tgm = BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException:
        logging.warning(f"Warning: Channel {c} not found")
        return None
    # Leider scheint tgme_widget_message_service_date erst nachgeladen zu werden; 
    # alternativ: nimm das Datum des frühesten Posts
    if tgm.select_one("time.time") is not None:
        timestamp = isoparse(tgm.select_one("time.time")['datetime']).isoformat()
        channel_info['created'] = timestamp
    return channel_info


def tgc_clean(cname):
    """
    Helper function returning a sanitized Telegram channel name in lowercase.

    Parameters:
        cname (str): Telegram channel name or URL.

    Returns:
    str: Lower-case of the extracted channel name.
    """
    # Convert to lower case
    name = cname.lower()
    
    # Define the regex patterns
    tme_pattern = re.compile(r"t\.me/s/")
    extract_pattern = re.compile(r"(?<=t\.me/)[a-zäöüß0-9_]+")
    sanitize_pattern = re.compile(r"[a-zäöüß0-9_]+")
    if tme_pattern.search(name):
        n = extract_pattern.search(name).group(0)
    else:
        n = sanitize_pattern.search(name).group(0)
        
    return n

def get_channel_from_url(channel:str):
    return re.search(r"(?<=t\.me\/).+(?=\/[0-9])",channel).group(0)

def tg_post_parse(b):
    # Liest aus dem HTML-Code eines einzelnen Posts
    # Immer vorhanden: 
    # Postnummer, Zeitstempel (auch wenn er in Einzel-Posts als datetime auftaucht und in Channel_seiten als time)
    b_id = int(re.search(r'[0-9]+$', b.select_one("a.tgme_widget_message_date")['href']).group())
    type = 'other'
    logging.info(f"Parse Telegram-Post Nr. {b_id}")
    if b.select_one("time.time") is not None:
        timestamp = isoparse(b.select_one("time.time")['datetime']).isoformat()
    else: # Einzel-Post
        timestamp = isoparse(b.select_one("time.datetime")['datetime']).isoformat()
    # 
    if b.select_one("span.tgme_widget_message_views") is not None:
        views = extract_k(b.select_one("span.tgme_widget_message_views").get_text())
    else:
        views = None
    if b.select_one("a.tgme_widget_message_date"):
        post_url = b.select_one("a.tgme_widget_message_date")['href']
        channel = get_channel_from_url(post_url)
    else:
        post_url = None
    textlinks = b.select("div.tgme_widget_message_text a")
    links = [a['href'] for a in textlinks if a['href'].startswith("http")]
    hashtags = [a['href'][3:] for a in textlinks if a['href'].startswith("?q=")]
    ### Die möglichen Content-Abschnitte eines Posts ###
    # Text
    if b.select_one("div.tgme_widget_message_text") is not None:
        text = b.select_one("div.tgme_widget_message_text").get_text()
        type = 'text'
    # Polls: Text der Optionen extrahieren
    elif b.select_one("div.tgme_widget_message_poll") is not None:
        text = b.select_one("div.tgme_widget_message_poll_question").get_text()
        for bb in b.select("div.tgme_widget_message_poll_option_text"):
            text += "\n* " + bb.get_text() 
        type = 'poll'
    else:
        text = None

    # Jetzt die Medien. 
    media = []
    
    # Sticker (Beispiel: https://t.me/telegram/23)
    if b.select_one("div.tgme_widget_message_sticker_wrap") is not None:
        sticker_url = b.select_one("i.tgme_widget_message_sticker")['data-webp']
        media.append({
            'type': 'image',
            'url': sticker_url,
                    # 'image': base64.b64encode(requests.get(sticker_url).content).decode('utf-8')
            })
        type = 'sticker'

    # Photo URL
    if b.select_one("a.tgme_widget_message_photo_wrap") is not None:
        photo_url = re.search(r"(?<=image\:url\(\').+(?=\')", b.select_one("a.tgme_widget_message_photo_wrap")['style']).group(0)
        media.append({'type': 'image',
                      'url': photo_url,
                    # 'image': base64.b64encode(requests.get(photo_url).content).decode('utf-8')
                    })
        type = 'photo'

    # Sprachnachricht tgme_widget_message_voice https://t.me/fragunsdochDasOriginal/27176
    if b.select_one('audio.tgme_widget_message_voice') is not None:
        # Link auf OGG-Datei
        voice_url = b.select_one('audio.tgme_widget_message_voice')['src']
        voice_duration = b.select_one('time.tgme_widget_message_voice_duration').get_text()
        media.append({
            'type': 'voice',
            'url': voice_url,
            'duration': voice_duration,
        })
        # Für Transkription immer lokale Kopie anlegen
        type = 'voice'

    # Video URL (Beispiel: https://t.me/telegram/46)
    # Wenn ein Thumbnail/Startbild verfügbar ist - das ist leider nur bei den
    # Channel-Seiten, nicht bei den Einzel-Post-Seiten der Fall - speichere
    # es ab wie ein Photo. 
    if b.select_one('video.tgme_widget_message_video') is not None:
        video_url = b.select_one('video.tgme_widget_message_video')['src']
        media.append({
            'type': 'video',
            'url': video_url,
        })
        type = 'video'
        if b.select_one('tgme_widget_message_video_thumb') is not None:
            video_thumbnail_url = re.search(r"(?<=image\:url\('\)).+(?=\')",b.select_one('tgme_widget_message_video_thumb')['style'].group(0))
            media.append({
                'type': 'image',
                'url': video_thumbnail_url,
                # Keine Bas64 aus Übersichtlichkeits-Gründen
                #'image': base64.b64encode(requests.get(video_thumbnail_url).content).decode('utf-8')
            })
    # Document / Audio URL? https://t.me/telegram/35
    # Link-Preview: https://t.me/s/telegram/15
    
    # Audio - kann ohne Anmeldung nicht gelesen werden
    if b.select_one("div.tgme_widget_message_document") is not None:
        text=b.select_one("div.tgme_widget_message_document_title").get_text()

    # Forwarded
    if b.select_one("a.tgme_widget_message_forwarded_from_name") is not None:
        forward_url = b.select_one("a.tgme_widget_message_forwarded_from_name")['href']
        forward_name = channel
        forward = {
            'url': forward_url,
            'name': forward_name,
        }
    else: 
        forward = None
    # Poll, Beispiel: https://t.me/wilhelmkachel/1079
    poll_type = b.select_one("div.tgme_widget_message_poll_type")
    if poll_type is not None:
        poll_type = poll_type.get_text() # None wenn nicht vorhanden
    if type == 'other':
        print(b_id)
    post_dict = {
        'channel': channel,
        'id': b_id,
        'url': post_url,
        'views': views, #  Momentaufnahme! Views zum Zeitpunkt views_ts
        'views_ts': datetime.now().isoformat(), # Zeitstempel für die Views
        'timedate': timestamp,
        'text': text,
        'type': type,
        'media': media,
        'forwards': forward,
        'poll': poll_type, 
        'links': links,
        'hashtags': [f"#{tag}" for tag in hashtags],
    }
    return post_dict

def tgc_read(cname, id):
    # Einzelnen Post lesen: URL erzeugen, aufrufen. 
    c = tgc_clean(cname)
    channel_url = f"https://t.me/{c}/{id}"
    return tgc_read_url(channel_url)

def tgc_read_url(channel_url):
    # Reads a single post from its URL
    # Supposes that the URL is well-formed. 
    channel_url += "?embed=1&mode=tme"
    response = requests.get(channel_url)
    response.raise_for_status()
    tgm = BeautifulSoup(response.content, 'html.parser')
    # Error message?
    logging.info(f"Lese Einzelpost: {channel_url}")
    print("'",end="")
    if tgm.select_one("div.tgme_widget_message_error") is not None: 
        logging.error(f"Fehler beim Lesen von {channel_url}")
        return None
    b = tgm.select_one("div.tgme_widget_message")
    return tg_post_parse(b)

def tgc_blockread(cname="telegram", id=None):
    """
    Reads a block of posts from the channel - normally 16 are displayed.
    If single parameter is set, read only the post id; return empty if it 
    does not exist. 

    Parameters:
    cname (str): Channel name as a string (non-name characters are stripped).
    id (int, optional): Number where the block is centered. If none is given, read last post.
    save (bool, default True): Saves images to an image folder.
    describe (bool, default True): Transcribes/describes media content
    single (bool, default False): Return a single post rather than up to 16

    Returns:
    list of dict: A list of dictionaries consisting of up to 16 posts.
    """
    if id is None:
        id = "" # Without a number, the most recent page/post is shown
    else:
        id = int(id)

    c = tgc_clean(cname)
    # Nur einen Post holen? Dann t.me/<channel>/<id>,
    # sonst t.me/s/<channel>/<id>
    channel_url = f"https://t.me/s/{c}/{id}"
    logging.info(f"Lese Telegram-Channel {c}, Block um den Post {id}")
    response = requests.get(channel_url)
    response.raise_for_status()
    tgm = BeautifulSoup(response.content, 'html.parser')

    block = tgm.select("div.tgme_widget_message_wrap") 
    posts = [tg_post_parse(b) for b in block]
    # Posts aufsteigend sortieren   
    posts.sort(key=lambda x: x['id'])
    return posts

def tgc_read_range(cname, n1=1, n2=None, save=False, describe = False):
    # Liest einen Bereich von Post n1 bis Post n2 
    # Zuerst: Nummer des letzten Posts holen
    profile = tgc_profile(cname)
    # Sicherheitscheck: erste Post-Nummer überhaupt schon gepostet?
    max_id = profile['n_posts']
    if n1 > max_id: 
        return None
    n = n1
    if n2 is None:
        n2 = max_id
    posts = []
    while n <= n2:
        max = n2
        new_posts = tgc_blockread(cname, n)
        for p in new_posts:
            if p['id'] > n2: 
                return posts
            if p['id'] >= n:
                posts.append(p)
                if p['id'] == n2:
                    return posts
        n = p['id']
    return posts

def tgc_read_number(cname, n = 20, cutoff = None, save=True, describe = True):
    # Liest eine Anzahl n von Posts, beginnend bei Post cutoff (wenn cutoff=None, dann den aktuellsten)
    # Zuerst: Nummer des letzten Posts holen
    profile = tgc_profile(cname)
    # Sicherheitscheck: erste Post-Nummer überhaupt schon gepostet?
    max_id = profile['n_posts']
    if cutoff is None: 
        cutoff = max_id
    elif cutoff > max_id: 
        return None
    posts = []
    while len(posts) < n: 
        # Blockread-Routine liest immer ein ganzes Stück der Seite
        new_posts = tgc_blockread(cname, cutoff)
        id_values = [post['id'] for post in new_posts]
        posts.extend(new_posts)  
        # Abbruchbedingung: erster Post erreicht
        if cutoff == 1: 
            break
        cutoff = cutoff - 16
        if cutoff < 1:
            cutoff = 1
    # Posts absteigend sortieren
    posts.sort(key=lambda x: x['id'], reverse=True)
    return posts

## Routinen zum Check der letzten 20(...) Posts eines Telegram-Channels
# analog zu check_handle in der check_bsky-Library
#
# Hinter den Kulissen werden Listen von Post-dicts genutzt

# Hilfsfunktion: Verwandelt die Telegram-Tabellen mit den Spalten
# video', 'photo', 'voice', 'sticker'
# in eine Tabelle mit der Spalte 'media':
# Liste mit dict-Elementen, jeweils mit 'type' und dann den Inhalten
def pivot_to_media(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for post in posts:
        if post.get('media'):
            continue
        media = []
        for media_type in ['video', 'photo', 'voice', 'sticker']:
            if post.get(media_type):
                media.append({'type': media_type, **post[media_type]})
                post.pop(media_type)
                post['type'] = media_type
        post['media'] = media
    return posts

# Das Gegenstück: Die Tabelle wieder breit machen
def pivot_from_media(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for post in posts:
        if not post.get('media'):
            continue
        for media in post['media']:
            type = media['type']
            # Drop type key from media dict
            media.pop('type')
            post[type] = media
    return posts

# Wrapper für die asynchrone Hydrate-Funktion
def tg_hydrate(posts: List[Dict[str, Any]], mdir = "./media") -> List[Dict[str, Any]]:
    # In den Telegram-Posts hat bislang dummerweise jeder Medien-Typ seine eigene Spalte.
    # Diese Logik funktioniert besser.
    # 
    # Außerdem braucht die Hydrate-Funktion die Spalte 'id', bisher hieß sie nr.
    # Deshalb überall umbenannt. 
    for p in posts:
        if 'nr' in p:
            p['id'] = p['nr']
            del p['nr']
    if 'media' not in posts[0] or posts[0]['media'] is None:
        posts = pivot_to_media(posts)
        hydrated_posts = asyncio.run(hydrate_async(posts, mdir))
        return pivot_from_media(hydrated_posts)
    else:
        hydrated_posts = asyncio.run(hydrate_async(posts, mdir))
        return hydrated_posts

# Wrapper für die asynchrone Evaluate-Funktion
def tg_evaluate(posts: List[Dict[str, Any]], check_texts: bool = True, check_images: bool = True) -> List[Dict[str, Any]]:
    # In den Telegram-Posts hat bislang dummerweise jeder Medien-Typ seine eigene Spalte. 
    # Diese Logik funktioniert besser.
    if 'media' not in posts[0] or posts[0]['media'] is None: 
        posts = pivot_to_media(posts)
        evaluated_posts = asyncio.run(evaluate_async(posts, check_texts=check_texts, check_images=check_images))
        return pivot_from_media(evaluated_posts)
    else:
        evaluated_posts = asyncio.run(evaluate_async(posts, check_texts=check_texts, check_images=check_images))
        return evaluated_posts
    
# Hilfsfunktion: Eingelesene Text-Spalten wieder in dict umwandeln   
def convert_to_obj(val):
    if pd.isna(val):
        return None
    try:
        return ast.literal_eval(val)
    except (ValueError, SyntaxError):
        return val    
    
# Hilfsfunktion: CSV einlesen und als df ausgeben
def tg_reimport_csv(fname):
    df = pd.read_csv(fname)
    # Beim Einlesen 'nr' in 'id' umbenennen (altes Format)
    if 'nr' in df.columns:
            if 'id' not in df.columns:
                df.rename(columns={'nr': 'id'}, inplace=True)
    # Diese Spalten sind dict:
    structured_columns = ['media', 'photo', 'sticker', 'video', 'voice', 'forwards', 'links', 'aiornot_ai_score', 'hive_visual_ai']
    for c in structured_columns:
        if c in df.columns:
            df[c] = df[c].apply(convert_to_obj)
    return df