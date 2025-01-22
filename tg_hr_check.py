from src.aichecker.check_tg import *
from src.aichecker.detectora import query_detectora
from src.aichecker.aiornot import query_aiornot
from src.aichecker.transcribe import convert_mp4_to_mp3, convert_ogg_to_mp3
from ast import literal_eval
import re

# KONSTANTEN
N = 100
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
    return df

def is_hr_url(url):
    if 'hr.de' in url:
        return True
    if 'hessenschau.de' in url:
        return True
    if 'hrinforadio.de' in url:
        return True
    return False

def find_links(text):
    # Regex, um Links aus Text zu extrahieren
    if text is None or text=="":
        return []
    urls = re.findall(r'https?://[^\s]+', text)
    return hr_links

if __name__ == "__main__":
    # Datei mit den Channels einlesen
    # Schau, ob es schon Daten gibt
    if not os.path.exists('tg-checks'):
        os.makedirs('tg-checks')
    filename = f'tg-checks/channels.csv'
    if os.path.exists(filename):
        channels_df = pd.read_csv(filename)
        print(f"Config-Datei mit {len(channels_df)} Kanälen")
        channels = channels_df['Kanal'].to_list()
    else:
        channels=['fragunsdochdasoriginal','freiheitffm']
    # Datei mit den Links, auf die geprüft werden soll
    # Durchsucht in den gefunden Links auf diese Strings (naiv).
    #
    # Strings sollten also z.B. hessenschau.de 
    filename = f'tg-checks/checks.csv'
    if os.path.exists(filename):
        checks_df = pd.read_csv(filename)
        checks = checks_df['Kanal'].to_list()
    else:
        channels=['hessenschau.de',
                  'hrinforadio.de',
                  "hr3.de",
                  'hrfernsehen.de',
                  'ardmediathek.hr',
                  'hr.de',
                  ]
    warning_links = []
    for c in channels: 
        existing_df = pd.DataFrame()
        profile = tgc_profile(c)
        if profile is None:
                print(f"Kein Konto mit dem Namen {c} gefunden.")
        else:
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
            filename = f'tg-checks/{c}.csv'
            if os.path.exists(filename):
                existing_df = reimport_csv(filename)
                start_post = max(existing_df['nr'])
                print(f"Dieser Kanal wurde schon einmal ausgelesen, zuletzt Post Nr.: {start_post} - seitdem {last_post-start_post} neue Posts")
            else: 
                start_post = last_post-N
                print(f"Noch nicht gespeichert. Importiere {N} Posts bis zum letzten: {last_post}.")        
            # Lies die aktuellsten Posts, sichere und analysiere sie
            #
            if start_post < last_post:
                print(f"Einlesen {start_post+1} bis {last_post}...")
                posts = tgc_read_range(c, start_post+1, last_post, save=False, describe= False)
                # Nach hr-Links suchen
                # Die Posts, die hr-Links enthalten, markieren
                # und später als Tabelle ausgeben, die dann von einem Watch-Programm 
                # beobachtet wird
                alerts=[]
                for post in posts:
                    # Links gegen Liste prüfen
                    for l in post['links']:
                        for ch in checks:
                            # Taucht der Link in der Liste auf?
                            alert = post
                            # Speichern, was verlinkt wurde
                            alert['alert'] = ch
                            alerts.append(alert)
                print(f"Neue Alerts: ")
                for a in alerts:
                    print(a)
                # Posts anhängen an das csv dieses Kanals
                alerts_df = pd.DataFrame(alerts)
                df = pd.DataFrame(posts)
                df = pd.concat([existing_df, df]).drop_duplicates(subset=['nr']).reset_index(drop=True)
                df.to_csv(f'tg-checks/{c}.csv', index=False)  # Save to CSV for example
    print("Ende Gelände.")
    df.to_csv(f'tg-checks/alerts.csv', index=False)
