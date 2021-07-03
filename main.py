from datetime import datetime, timedelta
from typing import Optional, Tuple, Iterable, TypeVar, Callable

from discord.ext import commands, tasks

import config
from data import load_database, save_database, Server, Channel

database = load_database()

bot = commands.Bot(command_prefix='!')


@bot.event
async def on_ready():
    print(f'Logged on as {bot.user}')

    update_loop.start()


@bot.command(name='save')
async def save(_):
    global database
    save_database(database)


@bot.command(name='here')
async def here(ctx: commands.Context):
    global database

    server = first(database.servers, lambda s: s.id == ctx.guild.id)
    if not server:
        server = Server(id=ctx.guild.id, channels=[])
        database.servers.append(server)

    channel = first(server.channels, lambda ch: ch.id == ctx.channel.id)
    if not channel:
        channel = Channel(id=ctx.channel.id)
        server.channels.append(channel)

    else:
        await ctx.channel.send(f'This channel is already configured')
        return

    save_database(database)

    await ctx.channel.send(f'OK, this channel is now configured')

    update_loop.restart()


@bot.command(name='gtfo')
async def gtfo(ctx: commands.Context):
    global database

    server = first(database.servers, lambda s: s.id == ctx.guild.id)
    if not server:
        await ctx.channel.send('This server is not registered with me')
        return

    channel = first(server.channels, lambda ch: ch.id == ctx.channel.id)
    if not channel:
        await ctx.channel.send('This channel is not configured for me')

    server.channels.remove(channel)

    save_database(database)

    # TODO: try to delete/unpin message
    await ctx.channel.send('OK, removed this channel from managed channels')


@tasks.loop(seconds=10)
async def update_loop():
    global database

    message_content = build_realm_message()

    for server in database.servers:
        for channel in server.channels:
            ch = bot.get_channel(channel.id)

            pins = await ch.pins()
            if len(pins) > 0:  # TODO: Handle multiple pins
                await pins[0].edit(content=message_content)
            else:
                msg = await ch.send(message_content)
                await msg.pin()


@bot.command(name='time-offset')
async def time_offset(ctx: commands.Context, arg: str):
    try:
        offset = int(arg)
    except ValueError:
        ctx.channel.send('The argument for `!time-offset` must be an integer')
        return

    global database
    database.time_offset = offset
    save_database(database)

    server_now = datetime.utcnow() + timedelta(hours=offset)

    await ctx.channel.send(f'''
OK, setting UWO server time offset to {offset} hours vs UTC.
Verify that current time in Vancouver, Canada (PDT) is **{server_now:%Y-%m-%d %H:%M}**, e.g. via https://bit.ly/UWOTime
''')


@bot.command(name='maintenance')
async def maintenance(ctx: commands.Context, *args: str):
    global database

    arg = ' '.join(args)

    if arg == 'clear':
        database.maintenance_time = None
        save_database(database)
        await ctx.channel.send('Maintenance time cleared')
        update_loop.restart()
        return

    try:
        database.maintenance_time = datetime.strptime(arg, '%Y-%m-%d %H:%M')
    except ValueError:
        await ctx.channel.send('Argument for `maintenance` command must be a date in ISO format (YYYY-MM-DD hh:mm)')
        return

    save_database(database)
    await ctx.channel.send('Maintenance time set')
    update_loop.restart()


def build_realm_message() -> str:
    global database

    server_now = datetime.utcnow() + timedelta(hours=database.time_offset)

    wc_prev, wc_next = world_clock_shifts(server_now)

    maint = database.maintenance_time
    if maint:
        maintenance_text = f'{maint:%Y-%m-%d %H:%M} ({format_delta(maint - server_now)})'
    else:
        maintenance_text = 'Not set'

    return f'''
UWO server time (PDT / Vancouver, Canada):
> **{server_now:%Y-%m-%d %H:%M:%S}**
_(All times and dates below use this timezone.)_

:wrench: **Maintenance**
> Next maintenance: **{maintenance_text}**

:cowboy: **North America**
> **W.I.P.**
> Current event: **Free trains**
> Investment: **Unavailable**

:peace: **Epic Sea Feud**
> **W.I.P.**

:pirate_flag: **Pirate Sea Feud**
> **W.I.P.**

:timer: **World clock**
> Next shift: **{wc_next:%Y-%m-%d %H:%M} ({format_delta(wc_next - server_now)})**
> Last shift: {wc_prev:%Y-%m-%d %H:%M} ({format_delta(wc_prev - server_now)})
'''


def world_clock_shifts(ref: datetime) -> Tuple[datetime, datetime]:
    next_change = next_clock_change(ref)
    return next_clock_change(next_change - timedelta(weeks=10)), next_change


def next_clock_change(since: datetime) -> datetime:
    if since.hour >= 21:
        since += timedelta(days=1)

    since = since.replace(hour=21, minute=0, second=0, microsecond=0)

    while since.weekday() != 3:
        since += timedelta(days=1)

    while not (22 <= since.day <= 28 and since.month % 2 == 0):
        since += timedelta(weeks=1)

    return since


def format_delta(delta: timedelta) -> str:
    delta, revd = (delta, False) if delta.total_seconds() > 0 else (-delta, True)

    d = delta.days
    m = int(delta.total_seconds() // 60)
    h, m = divmod(m, 60)
    h = h % 24

    if d >= 2:
        result = f'{d} days, '
    elif d == 1:
        result = '1 day, '
    else:
        result = ''

    result = f'{result} {h:02}:{m:02}'

    return result + ' ago' if revd else 'in ' + result


def delta_to_h_m(delta: timedelta) -> Tuple[int, int]:
    return int(delta.total_seconds() // 3600), int(delta.total_seconds() // 60)


T = TypeVar('T')


def first(source: Iterable[T], pred: Callable[[T], bool]) -> Optional[T]:
    for item in source:
        if pred(item):
            return item

    return None


bot.run(config.DISCORD_TOKEN)
