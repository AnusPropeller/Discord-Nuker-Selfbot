### Basic Information
Strategic Raid Self-bot Script for Discord that tries to minimize alerting the moderators using various means. <br/>
Built using the dev build of discord.py-self. <br/>
The exe file is a nuitka build that doesn't require installing any dependencies or using an IDE.
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
