# Proof-of-concept: KI-Check von Bluesky-Konten
#
# 12-2024 Jan Eggers

from src.aichecker.check_bsky import *

# Konstante 
d_thresh = .8 # 80 Prozent 
limit = 25 # Posts für den Check

if __name__ == "__main__":
    # Bluesky-Check
    handle_str = input("Erstes Handle mit diesen Zeichen wählen: ")
    handle = find_handles(handle_str)[0]
    print(handle)
    # Diese Funktion holt die Infos zum Profil 'handle':
    # Erwartet einen String, gibt ein dict zurück. 
    # Beschreibung: https://docs.bsky.app/docs/api/app-bsky-actor-get-profile
    # Manchmal existieren Felder wie 'description' nicht. 
    profile = call_get_profile(handle)
    author = profile['did']
    print(author)
    # Diese Funktion holt die Posts.
    # 'author' darf irgendwas sein: handle, did... wir nehmen die did
    # Gibt ein dict zurück: im Schlüssel 'feed' sind die einzelnen Posts gespeichert, 
    # im Key 'cursor' gibt es das Datum des frühesten abgefragten Posts zurück (es sei denn,
    # es sind weniger Posts als limit, dann ist cursor leer.)
    # Beschreibung: https://docs.bsky.app/docs/api/app-bsky-feed-get-author-feed 
    posts = call_get_author_feed(author, limit = limit)
    # In diesem Demo-Programm werden die Posts hier noch nicht ausgewertet. 
    # Das passiert in der Extra-Funktion check_handle unten.
    print(posts['cursor'])
    # Funktion prüft die letzten ```limit``` Posts (voreingestellt auf 20)
    # Erwartet ein Handle oder ein did  - wir nehmen DID
    # Gibt ein Dataframe zurück; Struktur ist oben in der Funktion beschrieben. 
    # Wichtigster Punkt: Ergebnis des KI-Checks in den Spalten
    # - 'detectora_ai_score': Detectora-Score des Post-Textes (als real)
    # - 'aiornot_ai_score': 
    df = check_handle(author, limit = limit)
    n_posts = len(df)
    print(f"\n\nAnalyse des Kontos @{handle} ({profile['displayName']}) seit {profile['createdAt']} - {profile['followersCount']} Follower")
    print(f"{profile.get('description','---')}\n")
    print(f'Anzahl der analysierten Posts: {n_posts}')
    print(f"Durchschnittliche KI-Text-Wahrscheinlichkeit: {df['detectora_ai_score'].mean()*100:.2f}%")
    detectora_posts_df = df[df['detectora_ai_score'] >= d_thresh]
    print(f"Anzahl von Posts über einer detectora-Schwelle von {d_thresh*100:.1f}%: {len(detectora_posts_df)}")
    image_posts = [post for post in df['aiornot_ai_score'].to_list() if post is not None]
    # Liste auspacken, nur die Dicts ohne None-Elemente
    image_list = [item for sublist in image_posts for item in sublist]
    ai_list = [item for item in image_list if item['score']!='human']
    if len(image_list) == 0: 
        p_ai = 0
    else: 
        p_ai = len(ai_list)/len(image_list) * 100
    print(f"Anzahl der Bilder: {len(image_list)}, verdächtig: {len(ai_list)} ({p_ai:.1f})%")
    # Jetzt die Daten abspeichern
    # Fals das Directory nicht existiert, anlegen
    if not os.path.exists('bsky-checks'):
        os.makedirs('bsky-checks')
        
    # Read existing file if it exists
    filename = f'bsky-checks/{handle}.csv'
    if os.path.exists(filename):
        existing_df = pd.read_csv(filename)
        df = pd.concat([existing_df, df]).drop_duplicates(subset=['uri']).reset_index(drop=True)
    
    df.to_csv(f'bsky-checks/{handle}.csv', index=False)  # Save to CSV for example
    
    