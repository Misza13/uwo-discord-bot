from datetime import datetime, timedelta
from typing import Optional, Tuple

from discord import Message
from discord.ext import commands, tasks

import config

bot = commands.Bot(command_prefix='!')


main_message: Optional[Message] = None

maintenance_time: Optional[datetime] = None


@bot.event
async def on_ready():
    print(f'Logged on as {bot.user}')

    channel = bot.get_channel(860824610441527306)

    pins = await channel.pins()
    if len(pins) > 0:
        global main_message
        main_message = pins[0]  # TODO: Handle multiple pins

    update_loop.start()


@tasks.loop(seconds=10)
async def update_loop():
    await update_main_message()


@bot.command(name='time-offset')
async def time_offset(ctx: commands.Context, arg: str):
    offset = int(arg)

    server_now = datetime.utcnow() + timedelta(hours=offset)

    await ctx.channel.send(f'''
OK, setting UWO server time offset to {offset} hours vs UTC.
Verify that current time in Vancouver, Canada (PDT) is **{server_now:%Y-%m-%d %H:%M}**, e.g. via https://bit.ly/UWOTime
''')


@bot.command(name='maintenance')
async def maintenance(ctx: commands.Context, *args: str):
    global maintenance_time

    arg = ' '.join(args)

    if arg == 'clear':
        maintenance_time = None
        update_loop.restart()
        return

    try:
        maintenance_time = datetime.strptime(arg, '%Y-%m-%d %H:%M')
    except ValueError:
        await ctx.channel.send('Argument for `maintenance` command must be a date in ISO format (YYYY-MM-DD hh:mm)')
        return

    update_loop.restart()


async def update_main_message():
    global main_message
    global maintenance_time

    channel = bot.get_channel(860824610441527306)

    server_now = datetime.utcnow() + timedelta(hours=-7)

    wc_prev, wc_next = world_clock_shifts(server_now)

    if maintenance_time:
        maintenance_text = f'{maintenance_time:%Y-%m-%d %H:%M} ({format_delta(maintenance_time - server_now)})'
    else:
        maintenance_text = 'Not set'

    message_content = f'''
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

    if main_message:
        await main_message.edit(content=message_content)
    else:
        main_message = await channel.send(message_content)
        await main_message.pin()


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


bot.run(config.DISCORD_TOKEN)
