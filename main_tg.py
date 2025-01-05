from src.aichecker.tg_check import *

if __name__ == "__main__":
    # Bluesky-Check
    #handle_str = input("Handle des Kanals eingeben: ")
    handle_str = "telegram"
    channels_dict = tgc_profile(handle_str)
    last_post = channels_dict['n_posts']
    print(channels_dict)
    # Lies eine Seite (mit bis zu 16 Posts), ohne Mediendateien anzulegen
    # und ohne Audios zu transkribieren
    posts = tgc_blockread(channels_dict['name'],nr=1, save=False, describe=False)
    print(posts)
    # Jetzt die aktuellsten Posts, mit Transkription/Mediendateien
    #posts = tgc_read(channels_dict['name'],nr=None, save=True, transcribe=True)
    #print(posts)
    # Nur ein einzelner Post
    posts = tgc_read(channels_dict['name'],nr=last_post)
    print(posts)
    # Über die Post-URL
    print(tgc_read_url('https://t.me/telegram/46',save=True, describe=True))
    posts = tgc_read_range(channels_dict['name'], last_post - 19, last_post, save = True, describe= True)
    print("Ende")