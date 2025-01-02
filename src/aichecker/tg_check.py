# tg_check.py
#
# Mistral-Übersetzung aus R (mein altes Rtgchannels-Projekt V0.11)
# Angepasst auf Listen statt Dataframes
#
# Noch nicht alles getestet und umgeschrieben
# 1-2025 Jan Eggers


import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re

def extract_k(n_str: str):
    if n_str.endswith('K'):
        try: 
            # Zahlen wie '5.06K', '1K'
            n = int(float(n_str[:-1]) * 1000)
        except:
            return None
    else: 
        try:
            n = int(n_str)
        except:
            return None
    return n

def tgc_profile(channel="ffmfreiheit"):
    """
    Generates base statistics for a Telegram channel.

    Parameters:
    channel (str)

    Returns:
    dict with the keys 'subscribers', 'photos', 'videos', 'links'

    Example: 
    profile = tgc_profile("wilhelmkachel")
    profile = tgc_profile("asdfasdfasdf") #  returns None
    """
    c = tgc_clean(channel)
    c_url = f"https://t.me/s/{c}"
    try:
        response = requests.get(c_url)
        response.raise_for_status()
        tgm = BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException:
        print(f"Warning: Channel {c} not found")
        return None
    channel_info = {}
    for info_counter in tgm.find_all('div', class_='tgme_channel_info_counter'):
        counter_value = info_counter.find('span', class_='counter_value').text.strip()
        counter_type = info_counter.find('span', class_='counter_type').text.strip()
        channel_info[counter_type] = extract_k(counter_value)
        
    return channel_info
    
"""
        # Read values from the info card
        counter_type = [span.get_text() for span in tgm.select('div.tgme_channel_info_counter span.counter_type')]
        counter_values = [extract_k(re.sub(r'[KMB]$', lambda m: {'K': 'e+03', 'M': 'e+06', 'B': 'e+09'}[m.group()], span.get_text()))
                          for span in tgm.select('div.tgme_channel_info_counter span.counter_value')]

        df = pd.DataFrame({'name': counter_type, 'values': counter_values}).pivot(index=None, columns='name', values='values').reset_index(drop=True)

        # Add id, description, title
        df['id'] = c
        df['title'] = tgm.select_one('div.tgme_channel_info_header_title').get_text()
        df['description'] = tgm.select_one('div.tgme_channel_info_description').get_text()

        # The last post is visible on this page. Gather its number.
        last_post_href = tgm.select('a.tgme_widget_message_date')[-1]['href']
        df['last_post_n'] = int(re.search(r'[0-9]+$', last_post_href).group())

        df['last_post_datetime'] = pd.to_datetime(tgm.select('time.time')[-1]['datetime'])

        # Now get the first post.
        tgm_firstpost = BeautifulSoup(requests.get(f"{c_url}/1").content, 'html.parser')
        df['created'] = pd.to_datetime(tgm_firstpost.select_one('time')['datetime'])

        # Calculate posts per week
        df['post_per_week'] = df['last_post_n'] / ((datetime.now() - df['created']).days / 7)

        if channels_df is None:
            channels_df = df
        else:
            channels_df = pd.concat([channels_df, df], ignore_index=True)

    return channels_df
"""

def tgc_clean(cname):
    """
    Helper function returning a sanitized Telegram channel name in lowercase.

    Parameters:
    cname (str or list): Telegram channel name or URL.

    Returns:
    str or list: Lower-case of the extracted channel name.
    """
    # Convert to lower case
    cname = [name.lower() for name in cname] if isinstance(cname, list) else cname.lower()

    # Define the regex patterns
    tme_pattern = re.compile(r"t\.me/s/")
    extract_pattern = re.compile(r"(?<=t\.me/)[a-zäöüß0-9_]+")
    sanitize_pattern = re.compile(r"[a-zäöüß0-9_]+")

    def process_name(name):
        if tme_pattern.search(name):
            return extract_pattern.search(name).group(0)
        else:
            return sanitize_pattern.search(name).group(0)

    if isinstance(cname, list):
        return [process_name(name) for name in cname]
    else:
        return process_name(cname)


#################### HIER SEYEN DRACHEN #####################
# All the untested functions follow here - they are just Mistral 
# translations/rewrites of the R stuff. 

def tgc_url(cname, nr):
    """
    Helper function returning a Telegram channel post URL.

    Parameters:
    cname (str): Telegram channel name or URL.
    nr (int): Post number.

    Returns:
    str: URL.
    """
    cname = cname.lower()
    match = re.search(r"[a-zäöüß0-9_]+", cname)
    if match:
        return f"https://t.me/s/{match.group(0)}/{nr}"
    return None




# Example usage
# test_list = tgc_blockread("telegram", nr=1)
# test_list = tgc_blockread("telegram")

def tgc_blockread(cname="telegram", nr=None, save=True):
    """
    Reads a block of posts from the channel - normally 16 are displayed.

    Parameters:
    cname (str): Channel name as a string (non-name characters are stripped).
    nr (int, optional): Number where the block is centered. If none is given, read last post.
    save (bool, default True): Saves images to an image folder.

    Returns:
    list of dict: A list of dictionaries consisting of up to 16 rows for each post.
    """
    if nr is None:
        nr = ""
    else:
        nr = int(nr)

    cname = tgc_clean(cname)
    tgc_url_ = tgc_url(cname, nr)

    response = requests.get(tgc_url_)
    response.raise_for_status()
    tgm = BeautifulSoup(response.content, 'html.parser')

    block = tgm.select("div.tgme_widget_message_wrap")
    block_list = []

    for b in block:
        b_nr = int(re.search(r'[0-9]+$', b.select_one("a.tgme_widget_message_date")['href']).group())
        forward = b.select_one("a.tgme_widget_message_forwarded_from_name")
        forward_url = forward['href'] if forward else None

        textlinks = b.select("div.tgme_widget_message_text a")
        links = [a['href'] for a in textlinks if a['href'].startswith("http")]
        hashtags = [a['href'][3:] for a in textlinks if a['href'].startswith("?q=")]

        photo_url_match = re.search(r"(?<=image\:url\('\)).+(?=\')", b.select_one("a.tgme_widget_message_photo_wrap")['style'])
        photo_url = photo_url_match.group(0) if photo_url_match else None

        post_dict = {
            'name': cname,
            'nr': b_nr,
            'url': b.select_one("a.tgme_widget_message_date")['href'],
            'timedate': pd.to_datetime(b.select_one("time.time")['datetime']),
            'text': b.select_one("div.tgme_widget_message_text").get_text(),
            'views': int(re.sub(r'[KMB]$', lambda m: {'K': 'e+03', 'M': 'e+06', 'B': 'e+09'}[m.group()], b.select_one("span.tgme_widget_message_views").get_text())),
            'forwards': forward_url,
            'links': links,
            'hashtags': [f"#{tag}" for tag in hashtags],
            'photo': photo_url
        }

        if save and photo_url:
            photo_file_search_string = r'\.[a-zA-Z]+$'
            photo_file = f"./media/{cname}_post_{b_nr}{re.search(photo_file_search_string, photo_url).group(0)}"
            os.makedirs(os.path.dirname(photo_file), exist_ok=True)
            with open(photo_file, 'wb') as f:
                f.write(requests.get(photo_url).content)

        block_list.append(post_dict)

    return block_list

# Examples: 
# test_list = tgc_collect("telegram")
# test_list = tgc_collect("telegram", first=1)
# test_list = tgc_collect("telegram", -100)

def tgc_collect(cname, first=1, save=False):
    """
    Collect hashtags, keywords, and links from a Telegram channel.

    Parameters:
    cname (str): Channel name to crawl.
    first (int): Earliest number of blocks to read (0 = all, negative reads number of posts).
    save (bool, default False): Saves images to an image folder.

    Returns:
    list of dict: A list of dictionaries containing the posts in ascending order.
    """
    collect_list = tgc_blockread(cname, save=save)
    min_nr = min(post['nr'] for post in collect_list)
    max_nr = max(post['nr'] for post in collect_list)

    if first < 1:
        first = max_nr + first + 1
    if first == 0:
        first = 1

    while first < min_nr:
        block_list = tgc_blockread(cname, min_nr - 8, save=save)
        block_list = [post for post in block_list if post['nr'] < min_nr]
        collect_list = block_list + collect_list
        min_nr = min(post['nr'] for post in block_list)
        print(".", end="")

    print(f"\nRead {len(collect_list)} posts\n")
    return [post for post in collect_list if post['nr'] >= first]


