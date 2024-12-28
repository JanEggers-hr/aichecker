import json
import pandas as pd
from atproto import Client, models
from detectora import query_detectora
from imagecheck import query_aiornot
from bildbeschreibung import gpt4_description

def aiornot_wrapper(did,embed):
    # Verpackung für die AIORNOT-Funktion: 
    # Checkt, ob es überhaupt ein Embed gibt, 
    # und ob es ein Bild enthält.
    # Wenn ja: nimmt das erste Bild und
    # erstellt KI-Beschreibung und KI-Einschätzung
    if embed is None or embed == '':
        return None
    images = getattr(embed,'images',None)
    if images is None:
        return None
    desc = []
    for i in images:
        # Construct an URL for the image thumbnail (normalised size)
        i_url = f"https://cdn.bsky.app/img/feed_thumbnail/plain/{did}/{i.image.ref.link}"
        aiornot_score = query_aiornot(i_url)
        gpt4_desc = gpt4_description(i_url)        
        desc.append({'aiornot_score': aiornot_score,
                     'gpt4_description': gpt4_desc})
    return desc
        

def fetch_user_posts(handle: str, limit: int = 100) -> list:
    # Initialize the Bluesky client (unauthenticated)
    client = Client(base_url="https://api.bsky.app")
    try:
        # Fetch the user ID from the handle
        profile = client.app.bsky.actor.get_profile({'actor': handle})
        user_id = profile.did
        
        # Initialize an empty list to store posts
        posts = []
        
        # Fetch timeline for the user (latest posts first)
        cursor = None
        while len(posts) < limit:
            if cursor is not None: 
                feed = client.app.bsky.feed.get_author_feed({'actor':user_id, 
                                                        'limit':(min(limit - len(posts), 50)), 
                                                        'cursor': cursor,
                                                        })
            else: 
                feed = client.app.bsky.feed.get_author_feed({'actor':user_id, 
                                                        'limit': (min(limit - len(posts), 100)), 
                                                        })
            if not feed['feed']:
                break
            cursor = feed['cursor']
            for item in feed['feed']:
                post = getattr(item,'post')
                # Extract basic post information
                post_data = {
                    'author_handle': getattr(post['author'],'handle',''),
                    'author_display_name': getattr(post['author'], 'display_name', ''),
                    'author_did': getattr(post['author'], 'did', ''),
                    'created_at': getattr(post['record'], 'created_at', ''),
                    # 'indexed_at': item[2],
                    
                    'text': getattr(post['record'], 'text', ''),
                    'uri': post['uri'],
                    'cid': post['cid'],
                    'like_count': post['like_count'],
                    'reply_count': post['reply_count'],
                    'repost_count': post['repost_count'],
                    'quote_count': post['quote_count'],
                    'language': getattr(post['record'], 'langs', [''])[0] if hasattr(post['record'], 'langs') else '',
                    # Embedded media: images, external, record
                    # Image alt, file, and URI
                    'embed': getattr(post['record'],'embed','')
                    # Embed URI and description
                    # 'external_description': getattr(post['embed']['external'],'description',''),
                    # 'external_uri': getattr(post['embed']['external'],'uri',''),
                    
                }
                posts.append(post_data)
        
        return posts[:limit]
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def check_handle(handle = 'lion-c.bsky.social', limit = 20):
    # Define the Bluesky handle and number of posts to fetch
    # Remove the @ before handle strings

    # Fetch the most recent posts from the specified user
    posts = fetch_user_posts(handle, limit)

    if not posts:
        print("No posts fetched. Please check the handle and try again.")
        return

    # Convert posts to a DataFrame
    df = pd.DataFrame(posts)

    # Now add probability check for each post text
    df['detectora_ai_score'] = df['text'].apply(query_detectora)
    
    # Now filter those 
    df['aiornot_ai_score'] = df.apply(lambda row: aiornot_wrapper(row['author_did'], row['embed']), axis=1)
    return df

if __name__ == "__main__":
    df = check_handle()
    print(f"Durchschnittliche KI-Text-Wahrscheinlichkeit: {df['detectora_ai_score'].mean()}")
    df.to_csv('user_posts.csv', index=False)  # Save to CSV for example
    