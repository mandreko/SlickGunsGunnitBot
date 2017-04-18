#!/usr/bin/env python
# -*- coding: utf-8 -*-
import atexit
import logging
import os
import sys

import praw
import psycopg2
import requests

from bs4 import BeautifulSoup
from posixpath import basename, dirname
from urllib import urlencode
from urlparse import urljoin, urlparse, parse_qs, urlunparse

LOG_LEVEL = os.environ.get('LOG_LEVEL')
USER_AGENT = os.environ.get('USERAGENT')
SUBREDDITS = os.environ.get('SUBS')
REDDIT_USER = os.environ.get('USERNAME')
REDDIT_PASSWORD = os.environ.get('PASSWORD')
REDDIT_CLIENT_ID = os.environ.get('CLIENTID')
REDDIT_CLIENT_SECRET = os.environ.get('CLIENTSECRET')
DB_STRING = os.environ.get('DATABASE_URL')
MESSAGE_TEMPLATE = """Direct Link: {1}


^(Original GunDeals Link: {0})

***
*I am a bot, and this action was performed automatically.*
(╯°□°)–︻╦╤─ - - -  pew pew pew!
"""

if not LOG_LEVEL:
    LOG_LEVEL = "INFO"
log_level = logging.getLevelName(LOG_LEVEL)
logging.basicConfig(level=log_level, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')

# Store cookies globally to be used site-wide
global_cookies = ""

# Setup database
postgres_url = urlparse(DB_STRING)

conn = psycopg2.connect(
    database=postgres_url.path[1:],
    user=postgres_url.username,
    password=postgres_url.password,
    host=postgres_url.hostname,
    port=postgres_url.port
)
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS public.oldposts (id text NOT NULL, CONSTRAINT "PK_id" PRIMARY KEY (id));')
conn.commit()
cur.close()

logging.debug("User Agent: %s" % USER_AGENT)
logging.debug("Username: %s" % REDDIT_USER)
logging.debug("Password: %s" % REDDIT_PASSWORD)
logging.debug("Client ID: %s" % REDDIT_CLIENT_ID)
logging.debug("Client Secret: %s" % REDDIT_CLIENT_SECRET)
logging.debug("DB String: %s" % DB_STRING)


@atexit.register
def close():
    logging.warning("Bot shutting down.")


def get_deal_url(url):
    global global_cookies
    logging.info("Getting URL for {0}".format(url.encode('utf-8')))

    # Read Original URL
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'}

    req = requests.get(url, headers=headers, verify=False)

    # Parse the HTML and find the "Go To Store" button
    soup = BeautifulSoup(req.text, 'html.parser')
    button = soup.find(id="go-to-store-button")

    # Return the GunDeals "deal" URL
    return urljoin("http://gun.deals", button.get('href'))


def resolve_redirect(url, original_url):
    global global_cookies
    logging.info("Getting Redirect URL for {0}".format(url.encode('utf-8')))

    # Read "deal" URL
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)',
               'Referer': original_url.encode('utf-8'),
               'Accept-Language': 'en-US,en;q=0.5'}
    req = requests.get(url, headers=headers, cookies=global_cookies, verify=False)

    return req.url


def sanitize_url(url):
    logging.info("Sanitizing URL {0}".format(url.encode('utf-8')))

    # Sanitize URL Query String
    parsed = urlparse(url.encode('utf-8'))
    logging.debug("Successfully parsed URL")

    filtered_path = parsed.path
    if parsed.netloc.endswith('amazon.com'):
        if basename(filtered_path).startswith('ref='):
            filtered_path = dirname(filtered_path)
    logging.debug("Removed Amazon referral code")

    qd = parse_qs(parsed.query, keep_blank_values=True)
    filtered_qs = dict((k, v) for k, v in qd.iteritems() if not k.startswith(
        ('utm_', 'src', 'cjaffilid', 'cjadv', 'cjaffsite', 'cjadvid', 'cjaffsite', 'tag', 'aid', 'avad', 'cm_mmc')))
    newurl = urlunparse([
        parsed.scheme,
        parsed.netloc,
        filtered_path,
        parsed.params,
        urlencode(filtered_qs, doseq=True),  # query string
        parsed.fragment
    ])
    logging.debug("Removed other strings")

    return newurl


def main():
    logging.warning("Bot starting up")

    reddit = praw.Reddit(client_id=REDDIT_CLIENT_ID,
                         client_secret=REDDIT_CLIENT_SECRET,
                         username=REDDIT_USER,
                         password=REDDIT_PASSWORD,
                         user_agent=USER_AGENT)

    logging.debug("Logged in as: %s" % reddit.user.me())

    subreddits = reddit.subreddit(SUBREDDITS)
    for submission in subreddits.stream.submissions():
        logging.info("URL: {0}".format(submission.url.encode('utf-8')))

        cur = conn.cursor()
        cur.execute("SELECT * FROM public.oldposts WHERE ID=%s", (submission.id,))

        gundeal_urls = ['gun.deals', 'slickguns.com']

        if submission.is_self or not any(x in submission.url for x in gundeal_urls):
            logging.info("Skipping post {0}. It's not a GunDeals link post.".format(submission.id))
            continue

        if cur.fetchone():
            logging.info("This post is already been commented on: {0}".format(submission.id))
            continue

        try:
            deal_url = get_deal_url(submission.url)
            direct_url = resolve_redirect(deal_url, submission.url)
            sanitized_url = sanitize_url(direct_url)

            message_text = MESSAGE_TEMPLATE.format(submission.url.encode('utf-8'), sanitized_url.encode('utf-8'))
            logging.info("Replying to post %s" % submission.id)
            submission.reply(message_text)

            # Add the post ID to the set of seen posts.
            logging.info("Inserting record %s into oldposts database" % submission.id)
            cur.execute("INSERT INTO public.oldposts (id) VALUES (%s)", (submission.id,))
            logging.info("Committing transaction")
            conn.commit()

            logging.info("Posted link for {0}".format(submission.url.encode('utf-8')))

        except:
            ex = sys.exc_info()[0]
            logging.warning(ex)
            logging.warning(repr(ex))
        finally:
            cur.close()


if __name__ == "__main__":
    main()
