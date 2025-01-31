# tg_check.py
#
# Mistral-Übersetzung aus R (mein altes Rtgchannels-Projekt V0.1.1)
# Angepasst auf Listen statt Dataframes
#
# 1-2025 Jan Eggers

import pandas as pd
import requests
from datetime import datetime
import http.client
import json
import os
import re
import base64
import logging
from .transcribe import gpt4_description, transcribe, convert_mp4_to_mp3, convert_ogg_to_mp3
from .check_wrappers import detectora_wrapper, aiornot_wrapper, transcribe_async, describe_async, detectora_async, aiornot_async
from .save_urls import save_url_async, save_url
import asyncio
import aiohttp

def igc_profile(username="mrbeast"):
    """
    Generates base statistics for an Instagram profile.

    Parameters:
    username (str)

    Returns:
    dict with the keys 
    - 'username'
    - 'biography'
    - 'profile_pic_url'
    - 'follower_count' (Number)
    - 'media_count' (number)
    - 'created' (date joined)

    Example: 
    profile = igc_profile("mrbeast")
    profile = igc_profile("nonexistentuser") # returns None
    """

    conn = http.client.HTTPSConnection("instagram-scraper-api2.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': os.getenv('RAPIDAPI_KEY'),
        'x-rapidapi-host': "instagram-scraper-api2.p.rapidapi.com"
    }

    try:
        conn.request("GET", f"/v1/info?username_or_id_or_url={username}&include_about=true", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8")).get('data', {})
    except Exception as e:
        logging.warning(f"Warning: User {username} not found. Error: {e}")
        return None

    if not data:
        return None

    profile_info = {
        'username': data.get('username'),
        'biography': data.get('biography'),
        'profile_pic_url': data.get('profile_pic_url'),
        'follower_count': data.get('follower_count'),
        'media_count': data.get('media_count'),
        'created': data.get('about', {}).get('date_joined')
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
        r"(?<=instagram\.com/)[a-zäöüß0-9_]+",
        r"(?<=www\.instagram\.com/)[a-zäöüß0-9_]+",
        r"(?<=http://instagram\.com/)[a-zäöüß0-9_]+",
        r"(?<=https://instagram\.com/)[a-zäöüß0-9_]+",
        r"(?<=http://www\.instagram\.com/)[a-zäöüß0-9_]+",
        r"(?<=https://www\.instagram\.com/)[a-zäöüß0-9_]+",
        r"(?<=@)[a-zäöüß0-9_]+",
        r"^[a-zäöüß0-9_]+$"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            return match.group(0)
    
    return None

def ig_post_parse(instagram_data, save=True, describe=True):
    posts = []
    for item in instagram_data['data']['items']:
        # Extract post details
        post_code = item.get('code', None)
        timestamp = datetime.fromtimestamp(item.get('taken_at_ts', 0)).isoformat()
        caption = item.get('caption', {}).get('text', None)
        
        # Extract media details
        images = []
        videos = []
        
        # Check for carousel media
        if 'carousel_media' in item:
            for media in item['carousel_media']:
                if 'image_versions' in media:
                    for image in media['image_versions']['items']:
                        images.append(image['url'])
                if 'video_url' in media:
                    videos.append(media['video_url'])
        else:
            # Single image or video
            if 'image_versions' in item:
                for image in item['image_versions']['items']:
                    images.append(image['url'])
            if 'video_url' in item:
                videos.append(item['video_url'])
        
        # Construct post dictionary
        post_dict = {
            'code': post_code,
            'timestamp': timestamp,
            'caption': caption,
            'images': images,
            'videos': videos,
        }
        
        # Save media if required
        if save:
            for idx, image_url in enumerate(images):
                save_url(image_url, f"{post_code}_image_{idx}")
            for idx, video_url in enumerate(videos):
                save_url(video_url, f"{post_code}_video_{idx}")
        
        # Describe media if required
        if describe:
            for image_url in images:
                image = base64.b64encode(requests.get(image_url).content).decode('utf-8')
                post_dict['image_description'] = gpt4_description(f"data:image/jpeg;base64, {image}")
            for video_url in videos:
                post_dict['video_transcription'] = transcribe(video_url)
        
        posts.append(post_dict)
    
    return posts

def igc_read_posts(cname, n=12):

    conn = http.client.HTTPSConnection("instagram-scraper-api2.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': os.getenv('RAPIDAPI_KEY'),
        'x-rapidapi-host': "instagram-scraper-api2.p.rapidapi.com"
    }

    posts = []
    pagination_token = ""

    while len(posts) < n:
        conn.request("GET", f"/v1.2/posts?username_or_id_or_url={cname}&pagination_token={pagination_token}", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))

        posts.extend(data['data']['items'])
        pagination_token = data.get('pagination', "")

        if not pagination_token:
            break

    return posts[:n]

# Die Post-Dicts hydrieren, d.h.: die URLs dazu laden und abspeichern

async def ig_hydrate_async(posts, mdir="./media"):
    # Liest die Files der Videos, Fotos, Voice-Messages asynchron ein. 
    async with aiohttp.ClientSession() as session:
        tasks = []
        for post in posts:
            if 'videos' in post: 
                for idx, video_url in enumerate(post['videos']):
                    save_url_async(session, video_url, f"{post['code']}_video_{idx}", mdir)
            if 'images' in post:
                for idx, image_url in enumerate(post['images']):   
                    save_url_async(session, image_url, f"{post['code']}_image_{idx}", mdir)
                    
        results = await asyncio.gather(*tasks)
        # Assign results back to posts
        index = 0
        for post in posts:
            if 'videos' in post:
                for idx, video_url in enumerate(post['videos']):
                    vfile = results[index]
                    post['videos'][idx] = {'url': video_url, 'file': vfile}
                    index += 1
            if 'images' in post:
                for idx, image_url in enumerate(post['images']): 
                    ifile = results[index]
                    post['images'][idx] = {'url': image_url, 'file': ifile}
                    image += 1
    return posts

def ig_hydrate(posts, mdir="./media"):
    return asyncio.run(ig_hydrate_async(posts, mdir))


def ig_hydrate_old(posts): 
    # Nimmt eine Liste von Posts und zieht die zugehörigen Dateien,
    # erstellt Beschreibungen und Transkriptionen. 
    # 
    # Fernziel: Asynchrone Verarbeitung. 
    for post in posts:
        # Transkription des Videos und Beschreibung des Thumbnails
        if 'videos' in post:
            for idx, video_url in enumerate(post['videos']):
                vfile = save_url(video_url, f"{post['code']}_video_{idx}")
                post['videos'][idx] = {'url': video_url, 'file': vfile, 'transcription': transcribe(vfile)}
        
        if 'images' in post:
            for idx, image_url in enumerate(post['images']):
                pfile = save_url(image_url, f"{post['code']}_image_{idx}")
                image = base64.b64encode(requests.get(image_url).content).decode('utf-8')
                post['images'][idx] = {'url': image_url, 'file': pfile, 'description': gpt4_description(f"data:image/jpeg;base64, {image}")}
    
    return posts


## Routinen zum Check der letzten 20(...) Posts eines Telegram-Channels
# analog zu check_handle in der check_bsky-Library
#
# Hinter den Kulissen werden Listen von Post-dicts genutzt

# Routine checkt eine Post-Liste, wie sie aus den ig_post_parse Routinen kommen.
# Wenn noch kein KI-Check vorliegt, wird er ergänzt. 
# Setzt allerdings voraus, dass die entsprechenden Inhalte schon abgespeichert sind.

async def ig_evaluate_async(posts, check_texts = True, check_images = True):
    tasks = []
    # Nimmt eine Liste von Posts und ergänzt KI-Einschätzung von Detectora
    # und AIORNOT. 
    for post in posts:
        if ('detectora_ai_score' not in post) and check_texts:
            # Noch keine KI-Einschätzung für den Text?
            post['detectora_ai_score'] = detectora_wrapper(post.get('caption', ''))

    for post in posts:
        if check_images:
            if post['video'] is not None and post['video'].get('file', None) is not None:
                vfile = post['video'].get('file')
                # Asynchron Transkription und KI-Bewertung anfordern
                tasks.append(transcribe_async(vfile))
                # Audiofile konvertieren und transkribieren transkribieren
                tasks.append(aiornot_async(convert_mp4_to_mp3(vfile), is_image=False))

            if post['photo'] is not None and post['photo'].get('file', None) is not None:
                pfile = post['photo']['file']
                # Bild aus Datei in ein Objekt laden
                with open(pfile, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                tasks.append(describe_async(f"data:image/jpeg;base64, {image_data}"))
                tasks.append(aiornot_async(pfile, is_image = True))

            if post['voice'] is not None and post['voice'].get('file', None) is not None:
                ofile = post['voice']['file']
                afile = convert_ogg_to_mp3(ofile)
                tasks.append(describe_async(afile))
                tasks.append(aiornot_async(afile, is_image = False))

            if post['sticker'] is not None and post['sticker'].get('file') is not None:  
                sfile = post['sticker']['file'] 
                with open(sfile, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')          
                tasks.append(describe_async(f"data:image/jpeg;base64, {image_data}"))
                tasks.append(aiornot_async(sfile, is_image = True))

        if post['text'] is not None and check_texts:
            tasks.append(detectora_async(post['text']))

    results = await asyncio.gather(*tasks)

        # Assign results back to posts
        # Die results stehen in der Reihenfolge, in der die Tasks generiert wurden, 
        # wir replizieren also im Prinzip die Schleife von oben. 
    index = 0
    for post in posts:
        if check_images:
            if post['video'] is not None and post['video'].get('file', None) is not None:
                post['video']['transcription'] = results[index]
                post['aiornot_ai_score'] = results[index+1]
                index += 2

            if post['photo'] is not None and post['photo'].get('file', None) is not None:
                post['photo']['description'] = results[index]
                post['aiornot_ai_score'] = results[index+1]
                index += 2

            if post['voice'] is not None and post['voice'].get('file', None) is not None:
                post['voice']['transcription'] = results[index]
                post['aiornot_ai_score'] = results[index+1]
                index += 2

            if post['sticker'] is not None and post['sticker'].get('file', None) is not None:
                post['sticker']['description'] = results[index]
                post['aiornot_ai_score'] = results[index+1]
                index += 2

        if post['text'] is not None and check_texts:
            post['detectora_ai_score'] = results[index]
            index +=1

    return posts



def ig_evaluate(posts, check_texts = True, check_images = True):
    return asyncio.run(ig_evaluate_async(posts, check_texts= check_texts, check_images=check_images))

def ig_evaluate_old(posts, check_texts=True, check_images=True):
    # Nimmt eine Liste von Posts und ergänzt KI-Einschätzung von Detectora
    # und AIORNOT. 
    for post in posts:
        if ('detectora_ai_score' not in post) and check_texts:
            # Noch keine KI-Einschätzung für den Text?
            post['detectora_ai_score'] = detectora_wrapper(post.get('caption', ''))
        if ('aiornot_ai_score' not in post) and check_images:
            max_ai_score = 0
            if post.get('videos'):
                # Alle Videos analysieren und den höchsten Score ermitteln
                for video_url in post['videos']:
                    ai_score = aiornot_wrapper(convert_mp4_to_mp3(video_url), is_image=False)
                    max_ai_score = max(max_ai_score, ai_score)
            if post.get('images'):
                # Alle Bilder analysieren und den höchsten Score ermitteln
                for image_url in post['images']:
                    ai_score = aiornot_wrapper(image_url, is_image=True)
                    max_ai_score = max(max_ai_score, ai_score)
            post['aiornot_ai_score'] = max_ai_score
    return posts


#### Handling der CSV

def retrieve_ig_csv(cname, path= "ig-checks"):
    fname = path + "/" + cname + ".csv"
    if os.path.exists(fname):
        df = pd.read_csv(fname)
        # reformat the columns containing dicts
        
        return df
    else:
        return None
    
def append_ig_csv(cname, posts_list, path = "ig-checks"):
    existing_df = retrieve_ig_csv(cname, path)
    df = pd.DataFrame(posts_list)
    if existing_df is not None: 
        df = pd.concat([existing_df, df]).drop_duplicates(subset=['uri']).reset_index(drop=True)
    df.to_csv(path + "/" + cname + ".csv", index=False)

