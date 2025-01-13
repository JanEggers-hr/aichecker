# tg_check.py
#
# Mistral-Übersetzung aus R (mein altes Rtgchannels-Projekt V0.1.1)
# Angepasst auf Listen statt Dataframes
#
# 1-2025 Jan Eggers


import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re
import base64
from .transcribe import gpt4_description, transcribe, convert_mp4_to_mp3, convert_ogg_to_mp3
from .check_wrappers import detectora_wrapper, aiornot_wrapper

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
    try:
        response = requests.get(c_url)
        response.raise_for_status()
        tgm = BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException:
        print(f"Warning: Channel {c} not found")
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
        print(f"Warning: Channel {c} not found")
        return None
    # Leider scheint tgme_widget_message_service_date erst nachgeladen zu werden; 
    # alternativ: nimm das Datum des frühesten Posts
    if tgm.select_one("time.time") is not None:
        timestamp = datetime.fromisoformat(tgm.select_one("time.time")['datetime']).isoformat()
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

def save_url(fname, name, mdir="./media"):
    # Die Medien-URLs bekommen oft einen Parameter mit übergeben; deswegen nicht nur
    # "irgendwas.ogg" berücksichtigen, sondern auch "irgendwas.mp4?nochirgendwas"
    content_ext = re.search(r"\.[a-zA-Z0-9]+(?=\?|$)",fname).group(0)
    content_file = f"{mdir}/{name}{content_ext}"
    try:
        os.makedirs(os.path.dirname(content_file), exist_ok=True)
    except:
        print(f"Kann kein Media-Directory in {mdir} öffnen")
        return None
    try:
        with open(content_file, 'wb') as f:
            f.write(requests.get(fname).content)
        return content_file
    except:
        print(f"Kann Datei {content_file} nicht schreiben")
        return None
    
def get_channel_from_url(channel:str):
    return re.search(r"(?<=t\.me\/).+(?=\/[0-9])",channel).group(0)

def tg_post_parse(b, save = True, describe = True):
    # Immer vorhanden: 
    # Postnummer, Zeitstempel (auch wenn er in Einzel-Posts als datetime auftaucht und in Channel_seiten als time)
    b_nr = int(re.search(r'[0-9]+$', b.select_one("a.tgme_widget_message_date")['href']).group())
    if b.select_one("time.time") is not None:
        timestamp = datetime.fromisoformat(b.select_one("time.time")['datetime']).isoformat()
    else: # Einzel-Post
        timestamp = datetime.fromisoformat(b.select_one("time.datetime")['datetime']).isoformat()
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
    # Polls: Text der Optionen extrahieren
    elif b.select_one("div.tgme_widget_message_poll") is not None:
        text = b.select_one("div.tgme_widget_message_poll_question").get_text()
        for bb in b.select("div.tgme_widget_message_poll_option_text"):
            text += "\n* " + bb.get_text() 
    else:
        text = None
    # Sticker (Beispiel: https://t.me/telegram/23)
    if b.select_one("div.tgme_widget_message_sticker_wrap") is not None:
        sticker_url = b.select_one("i.tgme_widget_message_sticker")['data-webp']
        sticker = {'url': sticker_url,
                    # 'image': base64.b64encode(requests.get(sticker_url).content).decode('utf-8')
                    }
        if describe:
            # GPT4o-mini versteht JPG, PNG, nicht animiertes GIF... und WEBP.
            image = base64.b64encode(requests.get(sticker_url).content).decode('utf-8')
            photo['description'] = gpt4_description(f"data:image/jpeg;base64, {image}")
        if save:
            sticker['file'] = save_url(sticker_url, f"{channel}_{b_nr}_sticker")
    else:
        sticker = None
    # Photo URL
    if b.select_one("a.tgme_widget_message_photo_wrap") is not None:
        photo_url = re.search(r"(?<=image\:url\(\').+(?=\')", b.select_one("a.tgme_widget_message_photo_wrap")['style']).group(0)
        photo = {'url': photo_url,
                    # 'image': base64.b64encode(requests.get(photo_url).content).decode('utf-8')
                    }
        if describe:
            image = base64.b64encode(requests.get(photo_url).content).decode('utf-8')
            photo['description'] = gpt4_description(f"data:image/jpeg;base64, {image}")
        if save:
            photo['file'] = save_url(photo_url, f"{channel}_{b_nr}_photo")
    else:
        photo = None
    # Sprachnachricht tgme_widget_message_voice https://t.me/fragunsdochDasOriginal/27176
    if b.select_one('audio.tgme_widget_message_voice') is not None:
        # Link auf OGG-Datei
        voice_url = b.select_one('audio.tgme_widget_message_voice')['src']
        voice_duration = b.select_one('time.tgme_widget_message_voice_duration').get_text()
        voice = {
            'url': voice_url,
            'duration': voice_duration,
        }
        # Für Transkription immer lokale Kopie anlegen
        if save or describe: 
            voice['file'] = save_url(voice_url, f"{channel}_{b_nr}_voice")
        if describe:
            voice['transcription'] = transcribe(voice['file'])
        
    else:
        voice = None
    # Video URL (Beispiel: https://t.me/telegram/46)
    # Wenn ein Thumbnail/Startbild verfügbar ist - das ist leider nur bei den
    # Channel-Seiten, nicht bei den Einzel-Post-Seiten der Fall - speichere
    # es ab wie ein Photo. 
    if b.select_one('video.tgme_widget_message_video') is not None:
        video_url = b.select_one('video.tgme_widget_message_video')['src']
        if b.select_one('tgme_widget_message_video_thumb') is not None:
            video_thumbnail_url = re.search(r"(?<=image\:url\('\)).+(?=\')",b.select_one('tgme_widget_message_video_thumb')['style'].group(0))
            video = {'url': video_url,
                    'thumbnail': video_thumbnail_url,
            }
            photo = {
                'url': video_thumbnail_url,
                # Keine Bas64 aus Übersichtlichkeits-Gründen
                #'image': base64.b64encode(requests.get(video_thumbnail_url).content).decode('utf-8')
            }
            if save or describe:
                # Thumbnail wird unter photo abgespeichert
                photo['file'] = save_url(video_thumbnail_url, f"{channel}_{b_nr}_photo")
        else:
            video = {'url': video_url,
                     }
        if save or describe:
            video['file'] = save_url(video_url, f"{channel}_{b_nr}_video")
        if describe:
            video['transcription'] = transcribe(video['file'])
            if photo is not None: 
                image = base64.b64encode(requests.get(video_thumbnail_url).content).decode('utf-8')
                photo['description'] = gpt4_description(f"data:image/jpeg;base64, {image}")
    else:
        video = None
    # Document / Audio URL? https://t.me/telegram/35
    # Link-Preview: https://t.me/s/telegram/15
    

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
    post_dict = {
        'channel': channel,
        'nr': b_nr,
        'url': post_url,
        'views': views, #  Momentaufnahme! Views zum Zeitpunkt views_ts
        'views_ts': datetime.now().isoformat(), # Zeitstempel für die Views
        'timedate': timestamp,
        'text': text,
        'photo': photo,
        'sticker': sticker,
        'video': video,
        'voice': voice,
        'forwards': forward,
        'poll': poll_type, 
        'links': links,
        'hashtags': [f"#{tag}" for tag in hashtags],
    }
    return post_dict

def tgc_read(cname, nr, save=True, describe = True):
    # Einzelnen Post lesen: URL erzeugen, aufrufen. 
    c = tgc_clean(cname)
    channel_url = f"https://t.me/{c}/{nr}"
    return tgc_read_url(channel_url, save, describe)

def tgc_read_url(channel_url, save=True, describe = True):
    # Reads a single post from its URL
    # Supposes that the URL is well-formed. 
    channel_url += "?embed=1&mode=tme"
    response = requests.get(channel_url)
    response.raise_for_status()
    tgm = BeautifulSoup(response.content, 'html.parser')
    # Error message?
    print("'",end="")
    if tgm.select_one("div.tgme_widget_message_error") is not None: 
        print(f"Fehler beim Lesen von {channel_url}")
        return None
    b = tgm.select_one("div.tgme_widget_message")
    return tg_post_parse(b, save, describe)

def tgc_blockread(cname="telegram", nr=None, save=True, describe=False):
    """
    Reads a block of posts from the channel - normally 16 are displayed.
    If single parameter is set, read only the post nr; return empty if it 
    does not exist. 

    Parameters:
    cname (str): Channel name as a string (non-name characters are stripped).
    nr (int, optional): Number where the block is centered. If none is given, read last post.
    save (bool, default True): Saves images to an image folder.
    describe (bool, default True): Transcribes/describes media content
    single (bool, default False): Return a single post rather than up to 16

    Returns:
    list of dict: A list of dictionaries consisting of up to 16 posts.
    """
    if nr is None:
        nr = "" # Without a number, the most recent page/post is shown
    else:
        nr = int(nr)

    c = tgc_clean(cname)
    # Nur einen Post holen? Dann t.me/<channel>/<nr>,
    # sonst t.me/s/<channel>/<nr>
    channel_url = f"https://t.me/s/{c}/{nr}"
    response = requests.get(channel_url)
    response.raise_for_status()
    tgm = BeautifulSoup(response.content, 'html.parser')

    block = tgm.select("div.tgme_widget_message_wrap") 
    posts = [tg_post_parse(b, save, describe) for b in block]
    # Posts aufsteigend sortieren   
    posts.sort(key=lambda x: x['nr'])
    return posts

def tgc_read_range(cname, n1=1, n2=None, save=True, describe = True):
    # Liest einen Bereich von Posts 
    # Zuerst: Nummer des letzten Posts holen
    profile = tgc_profile(cname)
    # Sicherheitscheck: erste Post-Nummer überhaupt schon gepostet?
    max_nr = profile['n_posts']
    if n1 > max_nr: 
        return None
    n = n1
    if n2 is None:
        n2 = max_nr
    posts = []
    while n <= n2:
        max = n
        new_posts = tgc_blockread(cname, n, save, describe)
        for p in new_posts:
            if p['nr'] > n2: 
                return posts
            if p['nr'] >= n:
                posts.append(p)
                if p['nr'] > max:
                    max = p['nr']
        n = max
    return posts

def tgc_read_number(cname, n = 20, cutoff = None, save=True, describe = True):
    # Liest eine Anzahl n von Posts, beginnend bei Post cutoff (wenn cutoff=None, dann den aktuellsten)
    # Zuerst: Nummer des letzten Posts holen
    profile = tgc_profile(cname)
    # Sicherheitscheck: erste Post-Nummer überhaupt schon gepostet?
    max_nr = profile['n_posts']
    if cutoff is None: 
        cutoff = max_nr
    elif cutoff > max_nr: 
        return None
    posts = []
    while len(posts) < n: 
        # Blockread-Routine liest immer ein ganzes Stück der Seite
        new_posts = tgc_blockread(cname, cutoff, save, describe)
        nr_values = [post['nr'] for post in new_posts]
        posts.extend(new_posts)  
        # Abbruchbedingung: erster Post erreicht
        if cutoff == 1: 
            break
        cutoff = cutoff - 16
        if cutoff < 1:
            cutoff = 1
    # Posts aufsteigend sortieren   
    posts.sort(key=lambda x: x['nr'])
    return posts

## Routinen zum Check der letzten 20(...) Posts eines Telegram-Channels
# analog zu check_handle in der check_bsky-Library
#
# Hinter den Kulissen werden Listen von Post-dicts genutzt

# Routine checkt eine Post-Liste, wie sie aus den tgc_read... Routinen kommen.
# Wenn noch kein KI-Check vorliegt, wird er ergänzt. 
# Setzt allerdings voraus, dass die entsprechenden Inhalte schon abgespeichert sind.
def check_tg_list(posts, check_images = True): 
    posts = [p for p in posts if p is not None]
    for post in posts:
        if 'detectora_ai_score' not in post:
            # Noch keine KI-Einschätzung für den Text?
            post['detectora_ai_score'] = detectora_wrapper(post['text'])
    # Leerzeile für den Fortschrittsbalken
    print()
    if not check_images:
        return
    # Okay, es geht weiter: Bilder auf KI prüfen
    for post in posts:
        if 'aiornot_ai_score' not in post: 
            if post['video'] is not None:
                # Audio des Videos analysieren
                fname = post['video'].get('file')
                post['aiornot_ai_score'] = aiornot_wrapper(convert_mp4_to_mp3(fname), is_image = False)
            elif post['photo'] is not None:
                # Bild analysieren
                post['aiornot_ai_score'] = aiornot_wrapper(post['photo'].get('file'), is_image = True)
            elif post['voice'] is not None:
                fname = post['voice'].get('file')
                post['aiornot_ai_score'] = aiornot_wrapper(convert_ogg_to_mp3(fname), is_image = False)
    return posts
# Wrapper für die check_tg_list Routine. 
# Gibt Resultate als df zurück, arbeitet aber hinter den Kulissen mit 
# einer Liste von dicts (anders als check_bsky)

def check_tgc(cname, n=20, cursor = None, check_images = True):
     
    exit("Funktion noch nicht definiert")
    return None

def retrieve_tg_csv(cname, path= "tg-checks"):
    fname = path + "/" + cname + ".csv"
    if os.path.exists(fname):
        df = pd.read_csv(fname)
        # reformat the columns containing dicts
        
        return df
    else:
        return None
    
def append_tg_csv(cname, posts_list, path = "tg-checks"):
    existing_df = retrieve_tg_csv(cname, path)
    df = pd.DataFrame(posts_list)
    if existing_df is not None: 
        df = pd.concat([existing_df, df]).drop_duplicates(subset=['uri']).reset_index(drop=True)
    df.to_csv(path + "/" + cname + ".csv", index=False)

