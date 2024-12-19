# Define the global posts list
posts = []

# Nicking the code to read from the bsky firehose here: 
# https://gist.github.com/stuartlangridge/20ffe860fee0ecc315d3878c1ea77c35
def append_post(json_data):
    # Parse JSON data and append to


#
# Basic idea: 
# - Get a feed.
# - Collect basic data on the author
# - Collect four weeks' posts
# - Analyse each post: 
#   - Check text with Hive and Detectora
#   - Check images with Hive and AIorNot
#   - Check video by isolating audio to AIorNot

import json
from atproto_client.models import get_or_create
from atproto import CAR, models
from atproto_firehose import FirehoseSubscribeReposClient, parse_subscribe_repos_message



class JSONExtra(json.JSONEncoder):
    """raw objects sometimes contain CID() objects, which
    seem to be references to something elsewhere in bluesky.
    So, we 'serialise' these as a string representation,
    which is a hack but whatevAAAAR"""
    def default(self, obj):
        try:
            result = json.JSONEncoder.default(self, obj)
            return result
        except:
            return repr(obj)

client = FirehoseSubscribeReposClient()

# all of this undocumented horseshit is based on cargo-culting the bollocks out of
# https://github.com/MarshalX/atproto/blob/main/examples/firehose/sub_repos.py
# and
# https://github.com/MarshalX/bluesky-feed-generator/blob/main/server/data_stream.py

def on_message_handler(message):
    commit = parse_subscribe_repos_message(message)
    if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
        return
    car = CAR.from_bytes(commit.blocks)
    for op in commit.ops:
        if op.action in ["create"] and op.cid:
            raw = car.blocks.get(op.cid)
            cooked = get_or_create(raw, strict=False)
            if cooked.py_type == "app.bsky.feed.post":
                # other types include "app.bsky.feed.like" etc which we ignore
                # note that this data does not include who posted this skeet
                # or possibly it does as a "CID" which you have to look up somehow
                # who the hell knows? not me
                
                print(json.dumps(raw, cls=JSONExtra, indent=2))


# Also look at this: 
# https://social-media-ethics-automation.github.io/book/bsky/ch04_data/05_data_python_platform/03_demo_data_from_platform.html

def main():
    client.start(on_message_handler)
    
    return






if __name__ == "__main__":
    main()