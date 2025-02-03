from src.aichecker.check_tg import *
from src.aichecker.detectora import query_detectora
from aichecker.je_aiornot import query_aiornot
from src.aichecker.transcribe import convert_mp4_to_mp3, convert_ogg_to_mp3
from ast import literal_eval

# KONSTANTEN
N = 25
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
    structured_columns = ['photo', 'sticker', 'video', 'voice', 'forwards', 'links']
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
    # Schau, ob es schon Daten gibt
    if not os.path.exists('tg-checks'):
        os.makedirs('tg-checks')
    filename = f'tg-checks/{handle}.csv'
    if os.path.exists(filename):
        existing_df = reimport_csv(filename)
        start_post = max(existing_df['nr'])
        print(f"Dieser Kanal wurde schon einmal ausgelesen, zuletzt Post Nr.: {start_post} - seitdem {last_post-start_post} neue Posts")
    else: 
        start_post = last_post-N+1
        print(f"Noch nicht gespeichert. Importiere {N} Posts bis zum letzten: {last_post}.")        
    # Lies die aktuellsten Posts, sichere und analysiere sie
    #
    print("Einlesen: ", end="")
    posts = tgc_read_range(handle_str, start_post, last_post)
    print() # für die Fortschrittsmeldung
    print("Inhalte sichern: ", end="")
    hydrated_posts = tg_hydrate(posts)
    print()
    print("Beschreiben und auf KI-Inhalt prüfen: ",end="")
    # Bearbeitet nur die Posts, für die Inhalte hinterlegt sind
    checked_posts = tg_evaluate(hydrated_posts)
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
        if post['video'] is not None:
            n_videos += 1
            ai_score = post['aiornot_ai_score'].get('confidence', 0)
            n_ai_videos += 1 if ai_score > AIORNOT_T else 0
        elif post['photo'] is not None:
            n_images += 1
            ai_score = post.get('aiornot_ai_score')
            if ai_score is None:
                ai_score = 0
            else:
                ai_score = ai_score['confidence']
            n_ai_images += 1 if ai_score > AIORNOT_T else 0
 
    print(f"\n\nIn den {N} Posts: ")
    print(f" - Texte: {n_texts}, davon KI-verdächtig: {n_ai_texts} (Schwelle: {DETECTORA_T})")
    print(f" - Bilder: {n_images}, davon KI-verdächtig: {n_ai_images} (Schwelle: {AIORNOT_T})")
    print(f"Ergebnis wird in 'tg-checks/{handle}.csv' mit abgespeichert. ")
    df = pd.DataFrame(posts)
    if ('existing_df' in globals()):
        df = pd.concat([existing_df, df]).drop_duplicates(subset=['nr']).reset_index(drop=True)
    df.to_csv(f'tg-checks/{handle}.csv', index=False)  # Save to CSV for example