import json
import pandas as pd
from atproto import Client, models

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
            feed = client.app.bsky.feed.get_author_feed({'actor':user_id, 
                                                        'limit':min(limit - len(posts), 50), 
                                                        'cursor':cursor,
                                                        })
            if not feed['feed']:
                break
            for item in feed['feed']:
                # Extract basic post information
                post_data = {
                    'author_handle': getattr(item[0][1], 'handle', ''),
                    'author_display_name': getattr(item[0][1], 'display_name', ''),
                    'author_did': getattr(item[0][1], 'did', ''),
                    'created_at': getattr(item[3], 'created_at', ''),
                    'indexed_at': item[2],
                    'text': getattr(item[3], 'text', ''),
                    'uri': item[4],
                    'cid': item[1],
                    'like_count': item[8],
                    'reply_count': item[10],
                    'repost_count': item[11],
                    'quote_count': item[9],
                    'language': getattr(item[3], 'langs', [''])[0] if hasattr(item[3], 'langs') else ''
                }
                posts.append(post_data)
            cursor = len(feed['feed'])
        
        return posts[:limit]
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def main():
    # Define the Bluesky handle and number of posts to fetch
    # Remove the @ before handle strings
    handle = 'lion-c.bsky.social'  # Replace with the desired handle
    limit = 100

    # Fetch the last 100 posts from the specified user
    posts = fetch_user_posts(handle, limit)

    if not posts:
        print("No posts fetched. Please check the handle and try again.")
        return

    # Convert posts to a DataFrame
    post_data = []
    for post in posts:
        post_data.append({
            'uri': post.uri,
            'cid': post.cid,
            'text': post.record.text,
            'created_at': post.record.createdAt,
            'author': handle  # Assuming you know the author's handle, otherwise fetch it from post record
        })

    df = pd.DataFrame(post_data)

    # Print or save the DataFrame as needed
    print(df)
    df.to_csv('user_posts.csv', index=False)  # Save to CSV for example

if __name__ == "__main__":
    main()