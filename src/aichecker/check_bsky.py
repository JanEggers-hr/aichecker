# Funktionen zum Check von Bluesky-Konten
#
# 12-2024 Jan Eggers


import json
import pandas as pd
from .transcribe import gpt4_description
from .check_wrappers import bsky_aiornot_wrapper, detectora_wrapper
import requests
import os

# Konstante 
d_thresh = .8 # 80 Prozent 
limit = 25 # Posts für den Check
        
def call_get_author_feed(author: str, limit: int=50, cursor= None) -> list:
    # Sucht den Post-Feed für das Bluesky-Konto author
    # author kann did oder handle sein
    # Gibt ein dict zurück aus: 
    # 'cursor'
    # 'feed' -> Liste der einzelnen Posts 
    data = {
        'actor': author,
        'limit': limit,
        'cursor': cursor,
    }
    headers = {
        'Content-Type': 'application/json',
        
    }
    try: 
        response = requests.get("https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed",
                              params=data,
                              headers=headers)
        if response.status_code == 200:
            # Success
            posts = response.json()
            # Falls weniger Posts existieren als das Limit, wird kein cursor zurückgegeben, 
            # in diesem Fall: cursor-Element noch dazupacken
            if not 'cursor' in posts: 
                posts['cursor'] = None
            return posts
        elif response.status_code == 400:
            print("Bluesky Public: Fehlerhafte API-Anfrage")
            return None
        elif response.status_code == 401:
            print("Zugriff auf Bluesky Public nicht erlaubt")
    except Exception as e:
        print("Fehler beim Verbinden mit der Bluesky-API:", str(e))
        return None
    return response['']

def call_get_profile(handle: str) -> list:
    # Gibt das gefundenen Profil zurück. 
    data = {
        'actor': handle,
    }
    headers = {
        'Content-Type': 'application/json',
        
    }
    try: 
        response = requests.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile",
                              params=data,
                              headers=headers)
        if response.status_code == 200:
            # Success
            return response.json()
        elif response.status_code == 400:
            print("Bluesky Public: Fehlerhafte API-Anfrage")
            return None
        elif response.status_code == 401:
            print("Zugriff auf Bluesky Public nicht erlaubt")
    except Exception as e:
        print("Fehler beim Verbinden mit der Bluesky-API:", str(e))
        return None
    return response['']

def fetch_user_posts(handle: str, limit: int = 100, cursor = None) -> list:
    profile = call_get_profile(handle)   
    did = profile['did']
    posts = []
    # Fetch timeline for the user (latest posts first)
    while len(posts) < limit:
        feed = call_get_author_feed(did, limit, cursor)
        if not feed['feed']:
            break
        cursor = feed['cursor']
        for item in feed['feed']:
            post =item['post']
            # Extrahiere Info zum einzelnen Post
            post_data = {
                'author_handle': post['author']['handle'], # Bluesky-Handle
                'author_display_name': post['author']['displayName'], # Klarname
                'author_avatar': post['author']['avatar'], # Bluesky-Link zum Avatar-Bild
                'author_did': post['author']['did'], # Bluesky-ID
                'created_at': post['record']['createdAt'], # Angelegt...
                # 'indexed_at': item[2],
                'text': post['record']['text'], # Text des Posts, falls vorhanden
                'uri': post['uri'], # Link auf den Post
                'cid': post['cid'], 
                'like_count': post['likeCount'], # Anzahl von Likes
                'reply_count': post['replyCount'], # Anzahl von Antworten
                'repost_count': post['repostCount'], # Anzahl von Reposts
                'quote_count': post['quoteCount'], # Anzahl von Zitat-Reposts
                'language': post['record'].get('langs') if 'langs' in post['record'] else '',
                # Embedded media: images, external, record 
                # (external sind Links ins Internet, images sind Bilder, record sind eingebettete Posts)
                # Image alt, file, and URI
                # Das Embed wird einfach so als dict in die Zelle geschrieben und gesondert ausgewertet
                'embed': post['record']['embed'] if 'embed' in post['record'] else ''
                # Embed URI and description
                # 'external_description': getattr(post['embed']['external'],'description',''),
                # 'external_uri': getattr(post['embed']['external'],'uri',''),
                
            }
            posts.append(post_data)
    
    return posts[:limit]
        
def check_handle(handle:str, limit:int = 20, cursor = None, check_images = True):
    # Konto und Anzahl der zu prüfenden Posts
    if handle == '':
        return None
    if handle[0]== '@':
        handle = handle[1:]

    # Fetch the most recent posts from the specified user
    posts = fetch_user_posts(handle, limit, cursor)

    if not posts:
        print(f"Keine Posts im Feed für Handle {handle}.")
        return

    # Convert posts to a DataFrame
    df = pd.DataFrame(posts)

    # Now add probability check for each post text
    if True: 
        print("Checke Texte:")
        df['detectora_ai_score'] = df['text'].apply(detectora_wrapper)
    
    # Now add "ai" or "human" assessment for images
    if check_images:
        print("\nChecke Bilder:")
        df['aiornot_ai_score'] = df.apply(lambda row: bsky_aiornot_wrapper(row['author_did'], row['embed']), axis=1)
    else:
        df['aiornot_ai_score'] = None
    print()
    return df

def call_find_handles(text):
    # Ruft die Bluesky-Public-API direkt auf und bekommt ein JSON zurück, das ein Element
    # actors mit einer Liste der gefundenen Konten enthält
    data = {
        'q': text,
    }
    headers = {
        'Content-Type': 'application/json',
        
    }
    try: 
        response = requests.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors",
                              params=data,
                              headers=headers)
        if response.status_code == 200:
            # Success
            return response.json()
        elif response.status_code == 400:
            print("Bluesky Public: Fehlerhafte API-Anfrage")
            return None
        elif response.status_code == 401:
            print("Zugriff auf Bluesky Public nicht erlaubt")
    except Exception as e:
        print("Fehler beim Verbinden mit der Bluesky-API:", str(e))
        return None
    return response['']
 
   
def find_handles(text):
    # Sucht Bluesky-Handles und gibt eine Liste von Handles zurück
    actors = call_find_handles(text)
    handles = [a['handle'] for a in actors['actors']]
    return handles 

