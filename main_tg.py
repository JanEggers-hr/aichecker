from src.aichecker.tg_check import *

if __name__ == "__main__":
    # Bluesky-Check
    handle_str = input("Handle des Kanals eingeben: ")
    channels_dict = tgc_profile(handle_str)
    print(channels_dict)