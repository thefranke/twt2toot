# twt2toot

This script synchronizes Tweets over to a Fediverse account, for instance on Mastodon. 

Install required libraries like this:
`pip3 install requests mastodon.py`

```
usage: twt2toot.py [-h] -t TWITTERHANDLE -a ACCESSTOKEN -i INSTANCE [-r RSSBRIDGE] [-d]

options:
  -h, --help            show this help message and exit
  -t TWITTERHANDLE, --twitterhandle TWITTERHANDLE
                        Your twitter name without the @
  -a ACCESSTOKEN, --accesstoken ACCESSTOKEN
                        The access token from your Fediverse instance
  -i INSTANCE, --instance INSTANCE
                        The Fediverse instance you're account is registered on, e.g. https://mastodon.social
  -r RSSBRIDGE, --rssbridge RSSBRIDGE
                        An RSS-Bridge instance with Twitter enabled
  -d, --dryrun          Do a test run without posting to the Fediverse
```

It [Mastodon.py](https://github.com/halcy/Mastodon.py) to post status messages and [RSS-bridge](https://github.com/RSS-Bridge/rss-bridge) to pull Twitter profile data via the JSON backend, so there is no need to have a Twitter access token for your profile. You will need a Fediverse account on an instance like `https://mastodon.social`. Log into your account and search for a development tab in the preferences to create an application that can control your account.

On Mastodon, navigate to *Preferences -> Development* and click on *New application*. Give your application any name you like (it'll appear underneath your posts as the application that was used to post a status). Under *Scopes* you will need to enable *write:media* and *write:status* (the only two actions performed by the script). Click *Submit* and select your application from the list on the next screen. From there, copy your *access token* which together with the instance address is what you need for the script to be able to post status messages.

The script will synchronize a batch of tweets initially and store the last synced tweet in a cache file. After the next run, the script will push only new tweets over.

If you want to see first what will be pushed you can do a `--dryrun` which will not post anything, only pull and present the data that will by synced.

Put the script in a Cron job and run it every 15 minutes.

# Custom adaptions

You may want to adapt `get_clean_status` to your needs. This function fetches the tweet in HTML and filters the content. It currently extracts raw URLs, removes `pic.twitter.com` links (images are added via upload) as well as video URLs and adds a "RT" in front of retweet URLs whose content though is not added to the status.

# Caveats

* Currently only posts images, as `mastodon.py` cannot post both videos and images in the same status.
* Cannot detect deleted tweets and remove them.
* Only processes quote tweets, not pure retweets.