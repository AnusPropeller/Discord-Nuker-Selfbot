### Basic Information
Has a hard time fetching all users. Will have to be restarted repeatedly to kick/ban all users in a large server. <br/>
Self-bot for nuking discord servers. <br/>
Tries to use Dyno commands if it has no perms. <br/>
Tries to remain under the radar for as long as possible. <br/>
Built using the dev build of discord.py-self. <br/>
The zip file is a Nuitka build that doesn't require installing any dependencies or using an IDE.
# Features
### Permission Based Deletion
If the user has permission, it deletes the following:
- Channels
- Roles
- Invites
- Emojis & Stickers
- Templates
- Automod Rules
- Webhooks
### Permission based User Removal
- Given kick permissions, the bot tries to prune all kickable members with >1 day of inactivity
- Given only kick permission, it does just that, same with ban permission
- Given both kick and ban permission, it alternates between kicking and banning.
  - Effectively removes users twice as fast.
  - Given time, the bot will go back and ban the kicked users.
- Tries to utilize Dyno bot as a last ditch effort to kick/ban users
  - When using commands, the bot tries to find the lowest useable voice-channel. If there are none it opts for the lowest usable text channel.
### User Silencing
- Given manage channel permissions, the bot mass edits all channels to deny read message and send message permissions.
- Given manage guild permissions, the bot adds an automod rule that blocks all messages, and times the sender out for a day.
### Order of Operations
1. Scrape guild members to a list / open a json file with user ids.
2. Deny channel permissions
3. Delete Automod Rules
4. Create Automod rule blocking messages
5. Delete Stickers, Emojis, Invites, Templates, Webhooks
6. Prune Members
7. Start Kicking/Banning Members
8. Delete Roles, Channels
9. Go back and Ban Kicked Members
10. Sync any Templates to current server status
# Running the Script
To use a .json file, drag it into the same directory. Follow the same json pattern as in my member scraper bot repo.
## Zip File
Download the zip file. <br/>
Extract the files. <br/>
Run /bot.dist/bot.exe
## via an IDE
This code will not work with vanilla discord.py, you need to install discord.py-self. <br/>
Run this command to install the discord.py-self branch: 
> pip install git+https://github.com/dolfies/discord.py-self@master#egg=discord.py-self[voice,speed] 
