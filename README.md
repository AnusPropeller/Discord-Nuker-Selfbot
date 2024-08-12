### Basic Information
Built using the dev build of discord.py-self.
The exe file is a nuitka build that doesn't require installing any dependencies or using an IDE.
### Features
Permission based deletion of various parts of a discord server.
- Channels
- Roles
- Invites
- Emojis & Stickers
- Templates
- Webhooks
### Dynamic User Removal
Utilizies both kicking and banning to remove users quickly.
If the bot has time, and permission in the guild, it will ban users after kicking them.
If the bot only has permission to exclusively kick or exclusively ban users (for some reason), it does that instead.
If the user doesn't have permissions to kick or ban, but has permission to use dyno to ban or kick it will do that instead. But, given both permissions with dyno, it will only ban users.
