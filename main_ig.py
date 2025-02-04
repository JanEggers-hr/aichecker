from src.aichecker.check_ig import *
from src.aichecker.detectora import query_detectora
from src.aichecker.transcribe import convert_mp4_to_mp3, convert_ogg_to_mp3

# KONSTANTEN
N = 10
DETECTORA_T = 0.8 # 80%
AIORNOT_T = 0.5 # 50% - AIORNOT selbst setzt den Wert sehr niedrig an.    
TEST = False


if __name__ == "__main__":
    logging.basicConfig(filename='logfile.log', level=logging.DEBUG)
    # ig_check
    #handle_str = "telegram"
    profile = None
    while profile is None: 
        handle_str = input("Handle des Kanals eingeben: ")
        handle = igc_clean(handle_str)
        profile = igc_profile(handle)
        if profile is None:
            print("Kein Konto mit diesem Namen gefunden.")
    print(f"Analysiert wird: {profile['full_name']}")
    print(f"{profile['biography']}")
    print()
    print(f"Folgt: {profile['following_count']}")
    print(f"Follower: {profile['follower_count']}")
    print(f"Posts: {profile['media_count']}")
    print(f"Angelegt: {profile['created']}")
    
    if not os.path.exists('ig-checks'):
        os.makedirs('ig-checks')
    filename = f'ig-checks/{handle}.csv'
    if os.path.exists(filename):
        existing_df = ig_reimport_csv(handle)
        last_post = max(existing_df['timestamp'])
        print(f"Dieser Kanal wurde schon einmal ausgelesen, zuletzt: {last_post}")
    else: 
        print(f"Noch nicht gespeichert. Importiere die aktuellsten {N} Posts.")        
    # Lies die aktuellsten Posts, sichere und analysiere sie
    #
    print("Einlesen: ", end="")
    posts = igc_read_posts(handle, n=N)
    print() # für die Fortschrittsmeldung
    print("Inhalte sichern und mit KI beschreiben: ", end="")
    hydrated_posts = ig_hydrate(posts,mdir = "ig-checks/media")
    print()
    print("Auf KI-Inhalt prüfen: ",end="")
    # Bearbeitet nur die Posts, für die Inhalte hinterlegt sind
    checked_posts = ig_evaluate(hydrated_posts)
    #
    print(f"Lese die Insta-Stories auf {handle}...")
    stories = igc_read_stories(handle)
    print(f"{len(stories)} Stories gefunden.")
    print(f"Lese die Highlight-Stories...")
    highlights = igc_read_highlights(handle)
    print(f"{len(highlights)} Stories gefunden.")
    ephemeral = stories + highlights
    print(f"{len(ephemeral)} ephemere Inhalte sichern und mit KI beschreiben: ", end="")  
    hydrated_ephemeral = ig_hydrate(ephemeral,mdir = "ig-checks/media")
    print()
    print("Auf KI-Inhalt prüfen: ",end="")
    checked_ephemeral = ig_evaluate(hydrated_ephemeral)
    # Zusammenfassung der Ergebnisse    
    checked_posts.extend(checked_ephemeral)
    n_posts = len(checked_posts)
    print(f"{n_posts} Posts und ephemere Inhalte geprüft.")
    # Zählen der Inhalte nach Typ und KI-Status
    n_images = 0
    n_ai_images = 0
    n_texts = 0
    n_ai_texts = 0
    n_videos = 0
    n_ai_videos = 0
    for post in checked_posts:
        if post.get('caption') is not None:
            n_texts += 1
            # Detectora-Score für diesen Text abrufen; wenn über der Schwelle, 
            # KI-Texte um eins hochzählen
            n_ai_texts += 1 if post.get('detectora_ai_score',0) > DETECTORA_T else 0
        if post.get('videos'):
            n_videos += 1
            ai_score = post.get('aiornot_ai_score', 0)
            n_ai_videos += 1 if ai_score > AIORNOT_T else 0
        elif post.get('images'):
            n_images += 1
            ai_score = post.get('aiornot_ai_score', 0)
            n_ai_images += 1 if ai_score > AIORNOT_T else 0
 
    print(f"\n\nIn den {N} Posts: ")
    print(f" - Texte: {n_texts}, davon KI-verdächtig: {n_ai_texts} (Schwelle: {DETECTORA_T})")
    print(f" - Bilder: {n_images}, davon KI-verdächtig: {n_ai_images} (Schwelle: {AIORNOT_T})")
    print(f"Ergebnis wird in 'ig-checks/{handle}.csv' mit abgespeichert. ")
    ig_append_csv(handle, checked_posts, path="ig-checks")
