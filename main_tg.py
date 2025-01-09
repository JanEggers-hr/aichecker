from src.aichecker.check_tg import *
from src.aichecker.detectora import query_detectora
from src.aichecker.imagecheck import query_aiornot

TEST = False

def count_posts(posts, threshold):
    text_count = 0
    score_count = 0
    
    for post in posts:
        if 'text' in post:
            text_count += 1
if __name__ == "__main__":
    # tg_check
    handle_str = input("Handle des Kanals eingeben: ")
    #handle_str = "telegram"
    handle = tgc_clean(handle_str)
    profile_dict = tgc_profile(handle)
    last_post = profile_dict['n_posts']
    if profile_dict is None:
            print("Kein Konto mit diesem Namen gefunden.")
            exit()
    print(f"Analysiert wird: {profile_dict['name']}")
    print(f"{profile_dict['description']}")
    print()
    print(f"Subscriber: {profile_dict['subscribers']}")
    print(f"Posts: {profile_dict['n_posts']}")
    print(f"Fotos: {profile_dict['photos']}")
    print(f"Videos: {profile_dict['videos']}")
    print(f"Links: {profile_dict['links']}")
    print()
    if TEST:
        # Lies eine Seite (mit bis zu 16 Posts), ohne Mediendateien anzulegen
        # und ohne Audios zu transkribieren
        posts = tgc_blockread(profile_dict['name'],nr=1, save=False, describe=False)
        # Jetzt die aktuellsten Posts, mit Transkription/Mediendateien
        #posts = tgc_read(channels_dict['name'],nr=None, save=True, transcribe=True)
        #print(posts)
        # Nur ein einzelner Post
        posts = tgc_read(profile_dict['name'],nr=last_post)
        print(posts)
        # Über die Post-URL
        print(tgc_read_url('https://t.me/telegram/46',save=True, describe=True))
        # Ein Bereich
        posts = tgc_read_range(profile_dict['name'], last_post - 19, last_post, save = True, describe= True)
        # Ein einzelner Post mit Video, Vorschaubild und Text
        posts = tgc_read_range("telegram", 295, 295, True, True)
        post = posts[0]
        print("KI-Check:")
        if 'detectora_ai_score' not in post:
            # Noch keine KI-Einschätzung für den Text?
            # post['detectora_ai_score'] = detectora_wrapper(post['text'])
            print(f"Detectora-Score: {query_detectora(post['text'])}")
        if 'aiornot_ai_score' not in post: 
            if post['photo'] is not None:
                # Bild analysieren
                # Das hier ist für die Galerie: AIORNOT kann derzeit
                # keine base64-Strings checken. 
                # Das Problem an den URLs der Photos ist: sie sind nicht garantiert. 
                base64_image = post['photo'].get('image',None) 
                image = f"data:image/jpeg;base64, {base64_image}"
            #post['aiornot_ai_score'] = aiornot_wrapper(post['photo'].get('url'))
            print("AIORNOT-AI-Score: {query_aiornot(post['photo']['url']}")
            # Videos kann man nur über das Audio auf KI checken. 
            # Muss ich erst noch implementieren. 
            # Die telegram-Videos haben kein Audio; deshalb ist das hier nicht schlimm
        print("Ende TEST")
    # Schau, ob es schon Daten gibt
    if not os.path.exists('tg-checks'):
        os.makedirs('tg-checks')
    filename = f'tg-checks/{handle}.csv'
    if os.path.exists(filename):
        existing_df = pd.read_csv(filename)
        print(f"Dieser Kanal wurde schon einmal ausgelesen, zuletzt: {max(existing_df[''])}")
    # Lies die 20 aktuellsten Posts, sichere und analysiere sie
    #
    # KONSTANTEN
    N = 10
    DETECTORA_T = 0.8 # 80%
    AIORNOT_T = 0.9 # 90%
    print("Einlesen/mit KI beschreiben: ", end="")
    posts = tgc_read_number(handle_str, N)
    print() # für die Fortschrittsmeldung
    print("Auf KI-Inhalt prüfen: ",end="")
    checked_posts = check_tg_list(posts, check_images = True)
    #
    n_images = 0
    n_ai_images = 0
    n_texts = 0
    n_ai_texts = 0
    for post in checked_posts:
         if post['text'] is not None:
              n_texts += 1
              # Detectora-Score für diesen Text abrufen; wenn über der Schwelle, 
              # KI-Texte um eins hochzählen
              n_ai_texts += 1 if posts.get('detectora_ai_score',0) > DETECTORA_T else 0
         if post['image'] is not None:
              n_images += 1
              try:
                  # Abruf des Keys kann scheitern, wenn kein Score, deshalb mit Try
                  ai_score = post['aiornot_ai_score']['ai']['confidence']
              except:
                   # Kein Key abrufbar? Score 0
                   ai_score = 0
              n_ai_images += 1 if ai_score > AIORNOT_T else 0
    print(f"In den {N} Posts: ")
    print(f" - Texte: {n_texts}, davon KI-verdächtig: (Schwelle: {n_ai_texts})")
    print(f" - Bilder: {n_images}, davon KI-verdächtig: {n_ai_images}")
    print(f"Ergebnis wird in 'tg-checks/{handle}.csv' mit abgespeichert. ")
    df = pd.DataFrame(posts)
    if ('existing_df' in globals()):
        df = pd.concat([existing_df, df]).drop_duplicates(subset=['uri']).reset_index(drop=True)
    df.to_csv(f'tg-checks/{handle}.csv', index=False)  # Save to CSV for example