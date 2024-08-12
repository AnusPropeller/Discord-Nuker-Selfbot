### Basic Information
Built using the dev build of discord.py-self.
The exe file is a nuitka build that doesn't require installing any dependencies or using an IDE.
## Features
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
- As a last ditch effort, it tries to use dyno bot to ban/kick users: must have permission
- Given only kick permission, it does just that, same with ban permission
- Given both kick and ban permission, it alternates between them to remove users quickly, and, given enough time, will go back and ban the kicked users.
### User Silencing
- Given manage channel permissions, the bot mass edits all channels to deny read message and send message permissions.
- Given manage guild permissions, the bot adds an automod rule that blocks all messages, and times the sender out for a day.
