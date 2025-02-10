from src.aichecker.check_ig import *
from src.aichecker.detectora import query_detectora
from src.aichecker.transcribe import convert_mp4_to_mp3, convert_ogg_to_mp3

import argparse
import pandas as pd

# KONSTANTEN
N = 30
DETECTORA_T = 0.8 # 80%
AIORNOT_T = 0.5 # 50% - AIORNOT selbst setzt den Wert sehr niedrig an.    
HIVE_T = 0.7
TEST = False



def parse_arguments():
    parser = argparse.ArgumentParser(description="Analyze Instagram channels for AI-generated content.")
    parser.add_argument('--channel', type=str, help='Handle of the Instagram channel to analyze.')
    parser.add_argument('--channels', type=str, help='Comma-separated list of Instagram channel handles to analyze.')
    parser.add_argument('--google-sheet', type=str, help='ID of a Google Sheet containing channel column.')
    parser.add_argument('--json', type=str, help='Path to JSON file containing the Google Sheet access credentials.')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()

    if args.google_sheet:
        df = pd.read_csv(args.google_sheet)
        channels = df['channel'].tolist()
    elif args.channels:
        channels = args.channels.split(',')
    elif args.channel:
        channels = [args.channel]
    else:
        channels = []

    while not channels:
        handle = igc_clean(input("Instagram-Channel eingeben: "))
        profile = igc_profile(handle)
        if profile is None:
            print(f"Channel: {handle} nicht gefunden")
        else:
            channels = [handle]

    for handle_str in channels:
        handle = igc_clean(handle_str)
        profile = igc_profile(handle)
        if profile is None:
            print(f"No account found for handle: {handle_str}")
            continue
        print(f"Analyzing: {profile['full_name']}")
        print(f"{profile['biography']}")
        print()
        print(f"Following: {profile['following_count']}")
        print(f"Followers: {profile['follower_count']}")
        print(f"Posts: {profile['media_count']}")
        print(f"Created: {profile['created']}")

        if not os.path.exists('ig-checks'):
            os.makedirs('ig-checks')
        filename = f'ig-checks/{handle}.csv'
        if os.path.exists(filename):
            existing_df = ig_reimport_csv(handle)
            last_post = max(existing_df['timestamp'])
            print(f"This channel has been analyzed before, last analyzed: {last_post}")
        else:
            print(f"Not previously saved. Importing the latest {N} posts.")

        print("Reading: ", end="")
        posts = igc_read_posts(handle, n=N)
        print()
        print("Hydrating - saving media: ", end="")
        hydrated_posts = ig_hydrate(posts, mdir="ig-checks/media")
        print()
        print("Checking for AI content: ", end="")
        checked_posts = ig_evaluate(hydrated_posts)
        print(f"Reading Instagram Stories on {handle}...")
        stories = igc_read_stories(handle)
        print(f"{len(stories)} Stories found.")
        print(f"Reading Highlight Stories...")
        highlights = igc_read_highlights(handle)
        print(f"{len(highlights)} Stories found.")
        ephemeral = stories + highlights
        print(f"{len(ephemeral)} ephemeral media for download: ", end="")
        hydrated_ephemeral = ig_hydrate(ephemeral, mdir="ig-checks/media")
        print()
        print("Checking for AI content: ", end="")
        checked_ephemeral = ig_evaluate(hydrated_ephemeral)

        checked_posts.extend(checked_ephemeral)
        n_posts = len(checked_posts)
        print(f"{n_posts} Posts and ephemeral contents checked.")

        n_images = 0
        n_ai_images = 0
        n_texts = 0
        n_ai_texts = 0
        n_videos = 0
        n_ai_videos = 0
        for post in checked_posts:
            if post.get('text') is not None:
                n_texts += 1
                n_ai_texts += 1 if post.get('detectora_ai_score', 0) > DETECTORA_T else 0
            for m in post['media']:
                if m.get('type') == 'video':
                    n_videos += 1  
                    aiornot = m.get('aiornot_ai_score',{}).get('score')
                    hive = m.get('hive_visual',{}).get('ai_score')
                    if hive is None:
                        if aiornot is not None: 
                            n_ai_videos += 1 if aiornot >= AIORNOT_T else 0
                    elif aiornot is None:
                        n_ai_videos += 1 if hive >= HIVE_T else 0
                    else:
                        n_ai_videos +=1 if hive>= HIVE_T and aiornot >= AIORNOT_T else 0
                if m.get('type') in ['sticker','image']:
                    n_images += 1  
                    aiornot = m.get('aiornot_ai_score',{}).get('score')
                    hive = m.get('hive_visual',{}).get('ai_score')
                    if hive is None:
                        if aiornot is not None: 
                            n_ai_images += 1 if aiornot >= AIORNOT_T else 0
                    elif aiornot is None:
                        n_ai_images += 1 if hive >= HIVE_T else 0
                    else:
                        n_ai_images +=1 if hive>= HIVE_T and aiornot >= AIORNOT_T else 0
        print(f"\n\nIn the {len(checked_posts)} posts and stories: ")
        print(f" - Texts: {n_texts}, AI-suspicious: {n_ai_texts} (Threshold: {DETECTORA_T})")
        print(f" - Images: {n_images}, AI-suspicious: {n_ai_images} (Threshold: {AIORNOT_T}/{HIVE_T})")
        print(f" - Videos: {n_videos}, AI-suspicious: {n_ai_videos} (Threshold {HIVE_T})")
        print(f"Results saved to 'ig-checks/{handle}.csv'.")
        ig_append_csv(handle, checked_posts, path="ig-checks")