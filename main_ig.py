from src.aichecker.check_ig import *
from src.aichecker.detectora import query_detectora
from src.aichecker.aiornot import query_aiornot
from src.aichecker.transcribe import convert_mp4_to_mp3, convert_ogg_to_mp3
from ast import literal_eval

# KONSTANTEN
N = 10
DETECTORA_T = 0.8 # 80%
AIORNOT_T = 0.5 # 50% - AIORNOT selbst setzt den Wert sehr niedrig an.    
TEST = False


# Hilfsfunktion: CSV einlesen und als df ausgeben
def convert_to_obj(val):
    if pd.isna(val):
        return None
    try:
        return literal_eval(val)
    except (ValueError, SyntaxError):
        return val


def reimport_csv(fname):
    df = pd.read_csv(fname)
    # Diese Spalten sind dict:
    structured_columns = ['photo', 'video']
    for c in structured_columns:
        df[c] = df[c].apply(convert_to_obj)
    # AIORNOT-Bewertung sind dict 
    df['aiornot_ai_score'] = df['aiornot_ai_score'].apply(convert_to_obj)
    return df

if __name__ == "__main__":
    # ig_check
    handle_str = input("Handle des Kanals eingeben: ")
    #handle_str = "telegram"
    handle = igc_clean(handle_str)
    profile = igc_profile(handle)
    if profile is None:
            print("Kein Konto mit diesem Namen gefunden.")
            exit()
    last_post = profile['media_count']
    print(f"Analysiert wird: {profile['full_name']}")
    print(f"{profile['biography']}")
    print()
    print(f"Follower: {profile['follower_count']}")
    print(f"Posts: {profile['media_count']}")
    
    if not os.path.exists('ig-checks'):
        os.makedirs('ig-checks')
    filename = f'ig-checks/{handle}.csv'
    if os.path.exists(filename):
        existing_df = retrieve_ig_csv(handle)
        start_post = max(existing_df['nr'])
        print(f"Dieser Kanal wurde schon einmal ausgelesen.")
    else: 
        start_post = last_post-N+1
        print(f"Noch nicht gespeichert. Importiere {N} Posts bis zum letzten: {last_post}.")        
    # Lies die aktuellsten Posts, sichere und analysiere sie
    #
    print("Einlesen: ", end="")
    posts = igc_read_posts(handle, n=N)
    print() # für die Fortschrittsmeldung
    print("Inhalte sichern und mit KI beschreiben: ", end="")
    hydrated_posts = ig_hydrate(posts)
    print()
    print("Auf KI-Inhalt prüfen: ",end="")
    # Bearbeitet nur die Posts, für die Inhalte hinterlegt sind
    checked_posts = ig_evaluate(hydrated_posts)
    #
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
    append_ig_csv(handle, checked_posts, path="ig-checks")
