# SlickGunsGunnitBot
Reddit bot for [https://www.reddit.com/r/gundeals](/r/gundeals) to give users direct links from SlickGuns URLs

## Reason
Recently (March 2016) many users in [https://www.reddit.com/r/gundeals](/r/gundeals) were complaining about people posting references to slickguns.com and having to click on the "Go To Store" button. Instead, they wanted direct links to the deal. I thought this would be a good reason to write my first reddit bot, and found it was quite easy to do.

## Overview
So this bot watches for new posts in the subreddit. The frequency of this check is defined by the `WAIT` variable. If there are new posts, it will see if they are URL links pointing to slickguns.com, and if so, visit the slickguns site, getting the direct URL. It then does some basic affiliate sanitization, to prevent users from spamming the subreddit with affiliate links. Once a reply is posted with the direct url, the reddit post id is added to a sqlite database, so it doesn't try to post again if the bot has to be restarted for some reason. 

## Persistence
To make sure the bot keeps running, I put it on a VPS. I setup a cron job to check to make sure it was running, and if not start it up. To do so, add the following lines to your `crontab -e` entry:
```
*/2 * * * * /home/<user>/SlickGunsGunnitBot/run.sh
```

This just covers the bases, in case Python throws some weird error that you weren't expecting, or your system gets rebooted for maintenance. It should gracefully restart automatically and keep providing a service that people hopefully value.
