from src.aichecker.check_tg import *
from src.aichecker.detectora import query_detectora
from src.aichecker.aiornot import query_aiornot

# KONSTANTEN
N = 20
DETECTORA_T = 0.8 # 80%
AIORNOT_T = 0.9 # 90%   
TEST = False

# Hilfsfunktion: CSV einlesen und als df ausgeben
def reimport_csv(fname):
    df = pd.read_csv(fname)
    # Diese Spalten sind dict:
    structured_columns = ['photo', 'sticker', 'video', 'voice', 'forward', 'links']
    for c in structured_columns:
        df[c] = df[c].apply(convert_to_obj)
    # AIORNOT-Bewertung sind dict 
    df['aiornot_ai_score'] = df['aiornot_ai_score'].apply(convert_to_obj)
    return df

if __name__ == "__main__":
    # tg_check
    handle_str = input("Handle des Kanals eingeben: ")
    #handle_str = "telegram"
    handle = tgc_clean(handle_str)
    profile = tgc_profile(handle)
    if profile is None:
            print("Kein Konto mit diesem Namen gefunden.")
            exit()
    last_post = profile['n_posts']
    print(f"Analysiert wird: {profile['name']}")
    print(f"{profile['description']}")
    print()
    print(f"Subscriber: {profile['subscribers']}")
    print(f"Posts: {profile['n_posts']}")
    print(f"Fotos: {profile['photos']}")
    print(f"Videos: {profile['videos']}")
    print(f"Links: {profile['links']}")
    print()
    if TEST:
        # Lies eine Seite (mit bis zu 16 Posts), ohne Mediendateien anzulegen
        # und ohne Audios zu transkribieren
        posts = tgc_blockread(profile['name'],nr=1, save=False, describe=False)
        # Jetzt die aktuellsten Posts, mit Transkription/Mediendateien
        #posts = tgc_read(channels_dict['name'],nr=None, save=True, transcribe=True)
        #print(posts)
        # Nur ein einzelner Post
        posts = tgc_read(profile['name'],nr=last_post)
        print(posts)
        # Über die Post-URL
        print(tgc_read_url('https://t.me/telegram/46',save=True, describe=True))
        # Ein Bereich
        posts = tgc_read_range(profile['name'], last_post - 19, last_post, save = True, describe= True)
        # Ein einzelner Post mit Video, Vorschaubild und Text
        posts = tgc_read_range("fragunsdochDasOriginal", 27170, 27170, True, True)
        post = posts[0]
        print("KI-Check:")
        if 'detectora_ai_score' not in post:
            # Noch keine KI-Einschätzung für den Text?
            # post['detectora_ai_score'] = detectora_wrapper(post['text'])
            print(f"Detectora-Score: {query_detectora(post['text'])}")
        if 'aiornot_ai_score' not in post: 
            if post['video'] is not None:
                # Audio des Videos analysieren
                post['aiornot_ai_score'] = aiornot_wrapper(post['video'].get('url'), is_image = False)
                print("Video: AIORNOT-Score")
                # Bild analysieren
                # Das hier ist für die Galerie: AIORNOT kann derzeit
                # keine base64-Strings checken. 
                # Das Problem an den URLs der Photos ist: sie sind nicht garantiert. 
                base64_image = post['photo'].get('image',None) 
                image = f"data:image/jpeg;base64, {base64_image}"
            post['aiornot_ai_score'] = aiornot_wrapper(post['photo'].get('url'))
            print("AIORNOT-AI-Score: {post['aiornot_ai_score']}")
            # Videos kann man nur über das Audio auf KI checken. 
            # Muss ich erst noch implementieren. 
            # Die telegram-Videos haben kein Audio; deshalb ist das hier nicht schlimm
        print("Ende TEST")
    # Schau, ob es schon Daten gibt
    if not os.path.exists('tg-checks'):
        os.makedirs('tg-checks')
    filename = f'tg-checks/{handle}.csv'
    if os.path.exists(filename):
        existing_df = reimport_csv(filename)
        max_nr = max(existing_df['nr'])
        print(f"Dieser Kanal wurde schon einmal ausgelesen, zuletzt Post Nr.: {max_nr} - seitdem {last_post-max_nr} neue Posts")
    else: 
        max_nr = last_post-N
    # Lies die aktuellsten Posts, sichere und analysiere sie
    #
    print("Einlesen/mit KI beschreiben: ", end="")
    posts = tgc_read_range(handle_str, max_nr+1, last_post)
    print() # für die Fortschrittsmeldung
    print("Auf KI-Inhalt prüfen: ",end="")
    checked_posts = check_tg_list(posts, check_images = True)
    #
    n_images = 0
    n_ai_images = 0
    n_texts = 0
    n_ai_texts = 0
    n_videos = 0
    n_ai_videos = 0
    for post in checked_posts:
        if post['text'] is not None:
            n_texts += 1
            # Detectora-Score für diesen Text abrufen; wenn über der Schwelle, 
            # KI-Texte um eins hochzählen
            n_ai_texts += 1 if post.get('detectora_ai_score',0) > DETECTORA_T else 0
        if post['photo'] is not None:
            n_images += 1
            ai_score = post['aiornot_ai_score'].get('confidence',0)
            n_ai_images += 1 if ai_score > AIORNOT_T else 0
        if post['video'] is not None:
            n_videos += 1
            ai_score = post['aiornot_ai_score'].get('confidence', 0)
            n_ai_videos += 1 if ai_score > AIORNOT_T else 0
 
    print(f"In den {N} Posts: ")
    print(f" - Texte: {n_texts}, davon KI-verdächtig: {n_ai_texts} (Schwelle: {DETECTORA_T})")
    print(f" - Bilder: {n_images}, davon KI-verdächtig: {n_ai_images} (Schwelle: {AIORNOT_T})")
    print(f"Ergebnis wird in 'tg-checks/{handle}.csv' mit abgespeichert. ")
    df = pd.DataFrame(posts)
    if ('existing_df' in globals()):
        df = pd.concat([existing_df, df]).drop_duplicates(subset=['uri']).reset_index(drop=True)
    df.to_csv(f'tg-checks/{handle}.csv', index=False)  # Save to CSV for example

