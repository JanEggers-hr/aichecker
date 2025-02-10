# scraper.py
#
# Skript arbeitet automatisch die Plattformen ab: Instagram, Telegram, Bluesky
# Wenn der Kanal noch nicht gelesen war: die N=30 letzten Posts.
#
# Steuerung und Ausgabe über das Google Sheet : 
# - 

from src.aichecker.check_ig import *
from src.aichecker.evaluate import eval_scans, export_to_xlsx

from datetime import datetime
import os
import argparse
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging

# KONSTANTEN
N = 30
T_DETECTORA = 0.8 # 80%
T_AIORNOT = 0.5 # 50% - AIORNOT selbst setzt den Wert sehr niedrig an.    
T_HIVE = 0.7
GSHEET = "1Tr1YU8zVu7AFBWy8HS9ZWVxFUgQPc51rvf-UlrXRXXM"
GSHEET_KEY = "~/.ssh/scrapers-272317-564f299b0cd4.json"
SAVE_PATH = '/../../html/frankruft/ig-checks'
SERVER_PATH = 'https://frankruft.de/ig-checks/media'

def parse_arguments():
    parser = argparse.ArgumentParser(description="Analyze Instagram channels for AI-generated content.")
    parser.add_argument('--channel', type=str, help='Handle of the Instagram channel to analyze.')
    parser.add_argument('--channels', type=str, help='Comma-separated list of Instagram channel handles to analyze.')
    parser.add_argument('--gsheet', type=str, help='ID of a Google Sheet containing channel column.')
    parser.add_argument('--jsonpath', type=str, help='Path to JSON file containing the Google Sheet access credentials.')
    parser.add_argument('--savepath', type=str, help='Path to save the output files.')
    parser.add_argument('--serverpath', type=str, help='Server path to refer files from outside')
    return parser.parse_args()

def write_statistics_to_gsheet(posts):
    sheet.update_cell(i,5, len(posts))
    # Letzter gelesener
    sheet.update_cell(i, 7, last_ts)
    # Auswertung der Posts in die Tabelle 
    eval = eval_scans(posts, T_DETECTORA, T_AIORNOT, T_HIVE)
    sheet.update_cell(i, 6, eval['n_images']+eval['n_videos']+eval['n_audios'])
    sheet.update_cell(i, 8, eval['n_ai_texts'])
    sheet.update_cell(i, 9, eval['n_ai_images'])
    sheet.update_cell(i, 10, eval['n_ai_videos'])
    sheet.update_cell(i, 11, eval['n_ai_audios'])   
    return

# Hilfsfunktion: Alle Bild- und Medien-URL umbauen auf Server frankruft.de/ig-checks/media/{file}
def serverize(posts, server_path=SERVER_PATH):
    for post in posts:
        for m in post['media']:
            filename = os.path.basename(m['file'])
            m['file'] = server_path + "/" + filename
    return posts

def remove_doubles(posts_new, posts_old):
    existing_ids = [post['id'] for post in posts_old]
    posts_new = [post for post in posts_new if post['id'] not in existing_ids]
    return posts_new


if __name__ == "__main__":
    args = parse_arguments()
    # Load the Google Sheet 
    if args.jsonpath:
        gsheet_key = args.jsonpath
    else:
        gsheet_key = GSHEET_KEY
    if args.gsheet:
        gsheet = args.gsheet
    else:
        gsheet = GSHEET
    if '~' in gsheet_key:
        gsheet_key = os.path.expanduser(gsheet_key)
    if args.savepath:
        SAVE_PATH = args.savepath
    if args.serverpath:
        SERVER_PATH = args.serverpath
    if args.channel:
        channels = [args.channel]

    # Los geht's 
    ts = datetime.now().strftime("%Y-%m-%d")
    # Anlegen
    save_dir = os.path.dirname(os.path.abspath(__file__)) + SAVE_PATH
    mdir = save_dir + '/media'
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    # Local Logfile
    logfile = save_dir + "/" + ts + '.log'
    logging.basicConfig(filename=logfile, level=logging.DEBUG)
    logging.info('Start Instagram-Scan: ' + ts)

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(gsheet_key, scope)
    client = gspread.authorize(creds)
    
    # Einstieg: Instagram lesen
    sheet = client.open_by_key(gsheet).worksheet("Instagram")
    # Jetzt die Namen der Kanäle einlesen, so lange, bis eine leere Zeile kommt. 
    # Read a cell
    i = 2
    channels = []
    # Maximal 1000 
    for i in range (2,1000): 
        value = sheet.cell(i, 1).value  # Read cell A1
        if value == None:
            continue
        handle = igc_clean(value)
        channels.append(value)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"Start Scan {value} um {ts}")
        # Startzeit eintragen
        sheet.update_cell(i, 2, ts)
        profile = igc_profile(handle)
        if profile == None:
            sheet.update_cell(i, 3, f"NICHT GEFUNDEN")            
            continue
        sheet.update_cell(i, 3, f"Bio: '{profile['biography']}'")
                
        # Bild abspeichern (ist nicht hydriert)
        image_url = profile.get('profile_pic_url')
        image_file = save_url(image_url,f"{handle}_profile",save_dir)
        # Gleich auf KI checken
        image_chk = hive_visual(image_file)
        sheet.update_cell(i, 3, f"KI Profilbild: {image_chk['ai_score']*100:.1f}%")
        filename = f'{save_dir}/{handle}.csv'
        # Checken: Gibt es schon ein CSV?
        if os.path.exists(filename):
            # Einlesen und in Posts konvertieren
            existing_df = ig_reimport_csv(filename)
            last_ts = max(existing_df['timestamp'])
            old_posts = existing_df.to_dict(orient='records')
            # Alle Posts 
            write_statistics_to_gsheet(old_posts)
            # Jetzt: Update starten
            posts = igc_read_posts_until(handle, last_ts)
        else: # kein CSV
            posts = igc_read_posts(handle, N)
            if len(posts) == 0: 
                sheet.update_cell(i, 3, f"KEINE POSTS")    
                continue
            old_posts = []
            last_ts = min(p['timestamp'] for p in posts)
        # Neue Posts hydrieren
        hydrated_posts = ig_hydrate(posts, mdir)
        # Anzahl der gespeicherten Medien ausgeben
        sheet.update_cell(i, 3, f"Neue Posts: {len(posts)}, checke auf KI...")
        checked_posts = ig_evaluate(hydrated_posts)
        write_statistics_to_gsheet(checked_posts)
        # Jetzt: Stories
        stories = igc_read_stories(handle)
        if len(stories) > 0:
            sheet.update_cell(i, 3, f"Stories: {len(stories)}, checke auf KI...")
            hydrated_stories = ig_hydrate(stories, mdir)
            checked_stories = ig_evaluate(hydrated_stories)
        else:
            checked_stories = []
        # Highlights: nur die neuen!
        highlights = igc_read_highlights(handle)
        # Schauen, welche schon in den Stories drin sind
        highlights_n = remove_doubles(highlights, old_posts)
        if len(highlights_n) > 0: 
            sheet.update_cell(i, 3, f"Neue Highlights: {len(highlights_n)}, checke auf KI...")
            hydrated_highlights = ig_hydrate(highlights_n, mdir)
            checked_highlights = ig_evaluate(hydrated_highlights)
        else:
            checked_highlights = []
        # DONE: Speichere ergänztes CSV
        all_checked = old_posts + checked_posts + checked_stories + checked_highlights
        if len(all_checked) == 0: 
            sheet.update_cell(i, 3, f"OK - kein Update")
            continue
        write_statistics_to_gsheet(all_checked)
        sheet.update_cell(i, 3, f"OK")
        all_posts = serverize(all_checked)
        df = pd.DataFrame(all_posts)
        df.to_csv(filename, index=False)
        # Exportiere CSV-Daten in XLSX
        xlsx_file = export_to_xlsx(all_checked, filename)
        # Dabei: Medienspalte "explodieren" (alles in eigene Zeile)
        # Trage im Google Sheet ein
        xlsx_url = SERVER_PATH + "/" + os.path.basename(xlsx_file)
        sheet.update_cell(i,4, f"{xlsx_url}")
        logging.info(f"Scan für {handle} erfolgreich abgeschlossen: {len(all_checked)} Posts, {len(checked_posts)} neue Posts, {len(checked_stories)} neue Stories, {len(checked_highlights)} neue Highlights")
        logging.info(f"XLSX-Datei: {xlsx_url}")
        # DONE
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Instagram-Scans für alle Kanäle erfolgreich abgeschlossen: {ts}")