#!/usr/bin/env python3

import re
import time
import json
import os
import html

import argparse
import requests
import mastodon

def get_cache_dir():
    home_dir = os.path.expanduser("~")
    cache_dir = ".cache/twt2toot"

    # make sure cache directory exists
    try:
        os.makedirs(cache_dir)
    except:
        pass

    return "%s/%s" % (home_dir, cache_dir)

def get_sync_file():
    return "%s/%s" % (get_cache_dir(), "sync.json")

# load last synced id from cache
def load_latest_id():
    sync_file = get_sync_file()

    j = {}
    try:
        with open(sync_file, "r") as in_file:
            j = json.load(in_file)
    except:
        pass

    return j.get("synced_until", 0)

# store latest synced id to cache
def store_latest_id(tweet_id):
    j = { "synced_until": tweet_id }

    sync_file = get_sync_file()

    with open(sync_file, "w") as out_file:
        json.dump(j, out_file, indent=2)

# download a file to a local cache directory and return local filename
def download_media(url):
    basename = url.split("?")[0].split("/")[-1]
    basename = "%s/%s" % (get_cache_dir(), basename)
    response = requests.get(url, allow_redirects=True)

    with open(basename, "wb") as f:
        f.write(response.content)

    return basename

# upload media files to mastodon and return id list
def upload_media_to_mastodon(mast, attachement_list, is_test_run):
    media_entries = []
    for media in attachement_list:
        mtype = media.get("mime_type")

        # only do pictures for now
        if mtype not in ["image/jpeg", "image/png"]:
            continue

        murl = media.get("url")
        file = download_media(murl)

        media_entries.append((mtype, file))

    if is_test_run:
        return media_entries

    media_ids = []
    for media in media_entries:
        upload_success = False
        while not upload_success:
            try:
                mtype, file = media
                media_dict = mast.media_post(file, mtype)
                media_id = media_dict.get("id")
                upload_success = True
            except Exception as e:
                print(e)
                time.sleep(1)

        media_ids.append(media_id)

    return media_ids

# transform html from tweet to simple text for status
def get_clean_status(status):
    # extract text in blockquote
    blockquotes = re.findall(r"<blockquote>.*</blockquote>", status, re.DOTALL)
    blockquote = blockquotes[0]

    def url_filter(match):
        url = match.group(1)

        if "pic.twitter.com" in url:
            return ""

        if "video/1" in url:
            return ""

        if "status/" in url:
            return "RT %s" % (url)

        return url

    # extract all urls and replace linked text
    blockquote = re.sub(r'<a href="([^"]*)"[^>]*>.*</a>', url_filter, blockquote, re.DOTALL)

    # Remove well-formed tags
    blockquote = re.sub(r"(<[^>]*>)", "", blockquote, re.DOTALL)

    return html.unescape(blockquote).strip()

# upload status to fediverse
def post_status(mast, status, media_ids):
    upload_success = False
    while not upload_success:
        try:
            mast.status_post(status=status, media_ids=media_ids)
            upload_success = True
        except Exception as e:
            print(e)
            time.sleep(1)

# sync all tweets
def sync_tweets(twitter_username, rss_bridge_instance, mastodon_access_token, mastodon_instance, is_test_run):
    latest_synced_id = load_latest_id()

    print("Last synced tweet:", latest_synced_id)

    # pull data for twitter handle
    feed_url = "%s/?action=display&bridge=Twitter&context=By+username&u=%s&norep=on&nopinned=on&format=Json" % (rss_bridge_instance, twitter_username)
    feed = requests.get(feed_url).json()

    # connect to mastodon
    mast = mastodon.Mastodon(access_token=mastodon_access_token, api_base_url=mastodon_instance)

    # go through every tweet and re-upload
    for f in reversed(feed.get("items", [])):
        # check if post already synced
        post_id = int(f.get("_rssbridge").get("id"))
        if post_id <= latest_synced_id:
            continue

        # skip retweets
        is_retweet = f.get("author").get("name").startswith("RT")
        if is_retweet:
            continue

        # postprocess tweet message
        status = get_clean_status(f.get("content_html"))

        # upload potential media attached to tweet
        media_ids = []
        media_ids = upload_media_to_mastodon(mast, f.get("attachments", {}), is_test_run)

        # post it (if there is any data)
        if status or media_ids:
            print("Syncing post:", status, media_ids, "\n\n")

            if not is_test_run:
                post_status(mast, status, media_ids)
                latest_synced_id = post_id

    if not is_test_run:
        store_latest_id(latest_synced_id)
        print("All synced")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--twitterhandle", help="Your twitter name without the @", default="", required=True)
    parser.add_argument("-a", "--accesstoken",   help="The access token from your Fediverse instance", default="", required=True)
    parser.add_argument("-i", "--instance",      help="The Fediverse instance you're account is registered on, e.g. https://mastodon.social", default="", required=True)
    parser.add_argument("-r", "--rssbridge",     help="An RSS-Bridge instance with Twitter enabled", default="https://wtf.roflcopter.fr/rss-bridge", required=False)
    parser.add_argument("-d", "--dryrun",        help="Do a test run without posting to the Fediverse", action="store_true")
    args = parser.parse_args()

    sync_tweets(args.twitterhandle, args.rssbridge, args.accesstoken, args.instance, args.dryrun)
