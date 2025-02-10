from src.aichecker.check_tt import *
from src.aichecker.detectora import query_detectora
from src.aichecker.transcribe import convert_mp4_to_mp3, convert_ogg_to_mp3

import argparse
import pandas as pd

# KONSTANTEN
N = 50
DETECTORA_T = 0.8 # 80%
AIORNOT_T = 0.5 # 50% - AIORNOT selbst setzt den Wert sehr niedrig an.    
HIVE_T = 0.7
TEST = False



def parse_arguments():
    parser = argparse.ArgumentParser(description="Analyze TikTok channels for AI-generated content.")
    parser.add_argument('--channel', type=str, help='Handle of the TikTok channel to analyze.')
    parser.add_argument('--channels', type=str, help='Comma-separated list of TikTok channel handles to analyze.')
    parser.add_argument('--google-sheet', type=str, help='URL to a Google Sheet containing channel, scan1, scan2, scan3 columns.')
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
        handle = ttc_clean(input("TikTok-Channel eingeben: "))
        profile = ttc_profile(handle)
        if profile is None:
            print(f"Channel: {handle} nicht gefunden")
        else:
            channels = [handle]

    for handle_str in channels:
        handle = ttc_clean(handle_str)
        profile = ttc_profile(handle)
        if profile is None:
            print(f"No account found for handle: {handle_str}")
            continue
        print(f"Analyzing: {profile['nickname']}")
        print(f"{profile['signature']}")
        print()
        print(f"Following: {profile.get('following_count', 'N/A')}")
        print(f"Followers: {profile.get('follower_count', 'N/A')}")
        print(f"Posts: {profile.get('media_count', 'N/A')}")
        print(f"Created: {profile.get('created', 'N/A')}")

        if not os.path.exists('tt-checks'):
            os.makedirs('tt-checks')
        filename = f'tt-checks/{handle}.csv'
        if os.path.exists(filename):
            existing_df = tt_reimport_csv(handle)
            last_post = max(existing_df['timestamp'])
            print(f"This channel has been analyzed before, last analyzed: {last_post}")
        else:
            print(f"Not previously saved. Importing the latest {N} posts.")

        print("Reading: ", end="")
        posts = ttc_read_posts(handle, n=N)
        print()
        print("Hydrating - saving media: ", end="")
        hydrated_posts = tt_hydrate(posts, mdir="tt-checks/media")
        print()
        print("Checking for AI content: ", end="")
        checked_posts = tt_evaluate(hydrated_posts)

        n_posts = len(checked_posts)
        print(f"{n_posts} Posts checked.")

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
        print(f"\n\nIn the {len(checked_posts)} posts: ")
        print(f" - Texts: {n_texts}, AI-suspicious: {n_ai_texts} (Threshold: {DETECTORA_T})")
        print(f" - Images: {n_images}, AI-suspicious: {n_ai_images} (Threshold: {AIORNOT_T}/{HIVE_T})")
        print(f" - Videos: {n_videos}, AI-suspicious: {n_ai_videos} (Threshold {HIVE_T})")
        print(f"Results saved to 'tt-checks/{handle}.csv'.")
        tt_append_csv(handle, checked_posts, path="tt-checks")