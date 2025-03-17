import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import yt_dlp
from collections import deque
import asyncio
import logging
import time

logging.basicConfig(level=logging.DEBUG)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

song_queue = deque()
current_song = None  # Текущий трек
player_message = None  # Сообщение с интерфейсом плеера

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'force-ipv4': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'opus',
        'preferredquality': '192',
    }],
    'cookiefile': 'cookies.txt'
}

""" class MusicPlayer(View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(emoji="⏮", style=discord.ButtonStyle.grey)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()

    @discord.ui.button(emoji="⏯", style=discord.ButtonStyle.green)
    async def play_pause_button(self, interaction: discord.Interaction, button: Button):
        voice_client = self.ctx.voice_client
        if voice_client.is_playing():
            voice_client.pause()
            button.emoji = "▶️"
        else:
            voice_client.resume()
            button.emoji = "⏸️"
        await interaction.response.defer()

    @discord.ui.button(emoji="⏭", style=discord.ButtonStyle.grey)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        global current_song
        if self.ctx.voice_client:
            self.ctx.voice_client.stop()
            current_song = None
        await interaction.response.defer()

    @discord.ui.button(emoji="⏹", style=discord.ButtonStyle.red)
    async def stop_button(self, interaction: discord.Interaction, button: Button):
        global current_song
        if self.ctx.voice_client:
            self.ctx.voice_client.stop()
            song_queue.clear()
            current_song = None
        await interaction.response.defer() """

@bot.event
async def on_ready():
    print(f"Бот {bot.user.name} готов!")

@bot.command(name="join")
async def join(ctx):
    if not ctx.author.voice:
        await ctx.send("Ти не в каналі!")
        return

    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
        await ctx.send(f"Підрубився до потужних хлопців з {channel.name}.")
    else:
        await ctx.voice_client.move_to(channel)

@bot.command(name="play")
async def play(ctx, url):
    global player_message
    voice_client = ctx.voice_client

    # Проверка подключения к голосовому каналу
    if not voice_client or not voice_client.is_connected():
        await ctx.send("Сначала присоединитесь к голосовому каналу через `!join`.")
        return

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)

            # Обработка плейлиста
            if "entries" in info:
                # Добавляем все треки из плейлиста в очередь
                entries = info["entries"]
                added_songs = 0
                for entry in entries:
                    if entry:  # Пропускаем возможные None-элементы
                        song_queue.append((entry["url"], entry["title"]))
                        added_songs += 1
                await ctx.send(f"🎶 В очередь добавлено **{added_songs} треков** из плейлиста.")
            else:
                # Обработка одиночного видео
                song_queue.append((info["url"], info.get("title", "Без названия")))
                await ctx.send(f"🎵 Трек добавлен в очередь: **{info['title']}**")

            # Если ничего не играет, запускаем воспроизведение
            if not voice_client.is_playing() and not current_song:
                await play_next_song(ctx)

            # Обновляем интерфейс плеера
            """ if not player_message:
                player = MusicPlayer(ctx)
                player_message = await ctx.send(view=player, embed=discord.Embed(description=" "))
            await update_player_interface(ctx) """

    except Exception as e:
        await ctx.send(f"❌ Ошибка: {str(e)}")

async def play_next_song(ctx):
    global current_song

    if not song_queue:
        return

    # Проверяем, подключен ли бот к голосовому каналу
    if ctx.voice_client is None or not ctx.voice_client.is_connected():
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("Ты не в голосовом канале, и бот не может подключиться!")
            return

    current_song = song_queue.popleft()
    url2, title = current_song

    def after_playing(e):
        global current_song
        current_song = None
        if e:
            print(f"Ошибка: {e}")
        asyncio.run_coroutine_threadsafe(play_next_song(ctx), bot.loop)

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    try:
        ctx.voice_client.play(
            discord.FFmpegPCMAudio(executable="ffmpeg", source=url2, **ffmpeg_options),
            after=after_playing
        )
        await ctx.send(f"🎶 Сейчас играет: {title}")
    except Exception as e:
        await ctx.send(f"❌ Ошибка воспроизведения: {str(e)}")
        current_song = None
        await play_next_song(ctx)


async def update_player_interface(ctx):
    global player_message, current_song

    if not player_message:
        return

    embed = discord.Embed(title="Музыкальный плеер", color=discord.Color.blue(), description=" ")
    if current_song:
        embed.add_field(name="Сейчас играет", value=current_song[1], inline=False, description=" ")
    else:
        embed.add_field(name="Статус", value="Ничего не играет", inline=False, description=" ")

    if song_queue:
        queue_list = "\n".join([f"**{i+1}.** {song[1]}" for i, song in enumerate(song_queue)])
        embed.add_field(name="Очередь", value=queue_list, inline=False, description=" ")

    await player_message.edit(embed=embed)

@tasks.loop(minutes=5)
async def check_voice_activity():
    for guild in bot.guilds:
        if guild.voice_client and not guild.voice_client.is_playing():
            await guild.voice_client.disconnect()
            print(f"Бот отключился от {guild.name} из-за бездействия.")

@bot.command(name="skip")
async def skip(ctx):
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Песня пропущена!")
    else:
        await ctx.send("Сейчас ничего не играет.")

@bot.command(name="stop")
async def stop(ctx):
    voice_client = ctx.voice_client
    if voice_client:
        voice_client.stop()
        song_queue.clear()
        await ctx.send("Воспроизведение остановлено и очередь очищена.")
    else:
        await ctx.send("Сейчас ничего не играет.")

@bot.command(name="leave")
async def leave(ctx):
    voice_client = ctx.voice_client
    if voice_client:
        await voice_client.disconnect()
        await ctx.send("Бот покинул голосовой канал.")
    else:
        await ctx.send("Бот не подключен к голосовому каналу.")

#@bot.event
#async def on_command_error(ctx, error):
   # await ctx.send(f"Ошибка: {str(error)}")
    


TOKEN = "MTMxMjQ1NDYwODk2NjEyNzYxNg.GLmq0v.ODlTZOWBi2__cA3ebwvumJRtYEv31d-nWQt4hU"
bot.run(TOKEN)
@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"Ошибка: {str(error)}")
    print(f"Ошибка: {str(error)}")