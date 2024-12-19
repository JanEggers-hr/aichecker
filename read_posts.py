import json
import pandas as pd
from atproto import Client, models

def fetch_user_posts(handle: str, limit: int = 100) -> list:
    # Initialize the Bluesky client (unauthenticated)
    client = Client()

    try:
        # Fetch the user ID from the handle
        profile = client.get_profile(handle)
        user_id = profile.did
        
        # Initialize an empty list to store posts
        posts = []
        
        # Fetch timeline for the user (latest posts first)
        cursor = None
        while len(posts) < limit:
            feed = client.app.bsky.feed.get_author_feed(actor=user_id, limit=min(limit - len(posts), 50), cursor=cursor)
            if not feed.posts:
                break
            posts.extend(feed.posts)
            cursor = feed.cursor
        
        return posts[:limit]
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def main():
    # Define the Bluesky handle and number of posts to fetch
    handle = '@lion-c.bsky.social'  # Replace with the desired handle
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