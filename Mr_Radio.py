import discord
from discord.ext import commands
from discord.ui import button, View
from discord import ButtonStyle, Interaction
from dotenv import load_dotenv
import os
from discord import FFmpegPCMAudio
from discord import PCMVolumeTransformer
import aiohttp

load_dotenv()
TOKEN = os.getenv("MR_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

default_prefix = "="
guild_prefix = {}
volume = 0.6
img_url = "https://imgs.search.brave.com/oYO8-wCU7td8awAWW9DRcYp5fjuRrpUMQ84j2upQGT4/rs:fit:860:0:0:0/g:ce/aHR0cHM6Ly9jbGlw/YXJ0LWxpYnJhcnku/Y29tL2ltZzEvMTYx/MDg1MS5naWY.gif"

bot = commands.Bot(command_prefix=default_prefix, intents=intents)

#url = "https://stream-174.zeno.fm/q97eczydqrhvv?zt=eyJhbGciOiJIUzI1NiJ9.eyJzdHJlYW0iOiJxOTdlY3p5ZHFyaHZ2IiwiaG9zdCI6InN0cmVhbS0xNzQuemVuby5mbSIsInJ0dGwiOjUsImp0aSI6InRhOHAxeTRDVDdHenYtN2NoeFQxRmciLCJpYXQiOjE3NDIwNDA3NDEsImV4cCI6MTc0MjA0MDgwMX0.MkjhfjpDcWKnjIHhgkq3SGxg9gH8U901CrsfPZ42PGM"
#url = "https://rfianglais96k.ice.infomaniak.ch/rfianglais-96k.mp3"

# Store guild-specific prefixes
@bot.event
async def on_guild_join(guild):
    if guild.id not in guild_prefix:
        guild_prefix[guild.id] = default_prefix  # Set default prefix for new guilds

@bot.event
async def on_guild_update(before, after):
    if before.id in guild_prefix:
        guild_prefix[after.id] = guild_prefix[before.id]  # Keep the same prefix if the guild is updated

@bot.event
async def on_guild_remove(guild):
    if guild.id in guild_prefix:
        del guild_prefix[guild.id]

## READY ##
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def hello(ctx):
    await ctx.send(f'Hello, {ctx.author.name}!')

# Change prefix
@bot.command()
async def prefix(ctx, new_prefix: str):
    global guild_prefix
    if len(new_prefix) == 1:  # Ensure the new prefix is a single character
        guild_prefix[ctx.guild.id] = new_prefix  # Store the prefix for the guild
        await ctx.send(f"Prefix changed to: {new_prefix}")
    else:
        await ctx.send("Please provide a single character as the new prefix.")

# Join a voice channel
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()     # Connect
        await ctx.send(f"{bot.user} has joined the channel {channel}")
    else:
        await ctx.send("You need to be in a voice channel first!")

# Leave a voice channel
@bot.command()
async def leave(ctx):
    if ctx.voice_client:    # Check if the bot is connected to a voice channel
        await ctx.voice_client.disconnect() # Disconnect
        await ctx.send("Disconnected from the Voice Channel!")
    else:
        await ctx.send("I am not connected to any voice channel!")

# Volume control
@bot.command()
async def vol(ctx, vol: float):
    if ctx.author.voice:
        if ctx.voice_client and ctx.voice_client.is_playing():
            # Is volume within range? (0-200)
            if 0.0 <= vol <= 200.0:
                ctx.voice_client.source.volume = vol / 100
                await ctx.send(f"Volume set to {int(vol)}%")
            else:
                await ctx.send("Please provide a volume between 0 to 100 (Max-200)")
        else:
            await ctx.send("No audio is playing right now!")
    else:
        await ctx.send("You need to be in a voice channel first!")

# Commands help
@bot.command()
async def rhelp(ctx):
    embed = discord.Embed(
        title= "Mr. Radio Commands",
        color=0x00ffcc
    )
    embed.add_field(name=f"{prefix}join", value="Join your voice channel", inline=False)
    embed.add_field(name=f"{prefix}leave", value="Leave the voice channel", inline=False)        
    embed.add_field(name=f"{prefix}next", value="Skip to the next radio station in the playlist.", inline=False)
    embed.add_field(name=f"{prefix}prev", value="Go back to the previous radio station in the playlist.", inline=False)
    embed.add_field(name=f"{prefix}jump <index>", value="Jump to a specific station in the playlist by index.", inline=False)
    embed.add_field(name=f"{prefix}pause", value="Pause the current radio station.", inline=False)
    embed.add_field(name=f"{prefix}resume", value="Resume the paused radio station.", inline=False)
    embed.add_field(name=f"{prefix}vol <volume>", value="Set the volume (0-200).", inline=False)
    embed.add_field(name=f"{prefix}radiourl <url> [volume]", value="Play a radio stream from a URL.", inline=False)
    embed.add_field(name=f"{prefix}radio <name/country/tag/language> <query>", value="Search and play radio stations by name, country, or tag.", inline=False)
    await ctx.send(embed=embed)

# ==========================================================================================================================    
# Plyaer Controls
class PlayerControls(View):
    def __init__(self, ctx, message):
        super().__init__(timeout=None)  # Disable timeout
        self.ctx = ctx
        self.message = message
        self.is_paused = False

    async def update_embed(self, station):
        embed = discord.Embed(title = "▶ Now Playing", 
                              description= f"**Radio Stream**\nVolume: {int(volume * 100)}%",
                              color = 0x00ffcc
                              )
        embed.set_thumbnail(url=station.get("favicon") if station.get("favicon") else (bot.user.avatar.url if bot.user.avatar else img_url))
        embed.set_author(name="Mr. Radio", icon_url=self.ctx.author.avatar.url if self.ctx.author.avatar else self.ctx.author.default_avatar.url)
        embed.add_field(name="Country", value=station.get("country", "Unknown"), inline=True)
        embed.add_field(name="Language", value=station.get("language", "Unknown").title(), inline=True)
        embed.set_footer(text=f"Use {prefix}help for more commands")

        # Update the message with the new embed
        if self.message:
            await self.message.edit(embed=embed, view=self)
        else:
            self.message = await self.ctx.send(embed=embed, view=self)  # If message is None, send a new message
       
    # Define buttons for player controls
    @discord.ui.button(label="⏮", style=ButtonStyle.primary)
    async def prev_button(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't control this player!", ephemeral=True)
            return
        if self.ctx.voice_client:
            await prev(self.ctx)
        else:
            await interaction.response.send_message("Bot is not connected to a voice channel!", ephemeral=True)
        await self.update_embed(self.ctx.voice_client.source.station)  # Update the embed with the current station info

    @discord.ui.button(label="⏸", style=ButtonStyle.primary)
    async def toggle_playback(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't control this player!", ephemeral=True)
            return
        if self.ctx.voice_client:
            if self.ctx.voice_client.is_playing():
                if self.ctx.voice_client.is_paused():
                    self.ctx.voice_client.resume()
                    self.is_paused = False
                    button.label = "⏸"  # Change label to pause
                    button.style = ButtonStyle.primary
                else:
                    self.ctx.voice_client.pause()
                    self.is_paused = True
                    button.label = "▶"  # Change label to play
                    button.style = ButtonStyle.success
            elif self.ctx.voice_client.is_paused():
                self.ctx.voice_client.resume()
                self.is_paused = False
                button.label = "⏸"
                button.style = ButtonStyle.primary
            else:
                await interaction.response.send_message("No audio is playing right now!", ephemeral=True)
                return
            await interaction.response.edit_message(view=self)  # Update the message with the new button state
            await self.update_embed(self.ctx.voice_client.source.station)  # Update the embed with the current station info
        else:
            await interaction.response.send_message("No audio is playing right now!", ephemeral=True)

    @discord.ui.button(label="⏭", style=ButtonStyle.primary)
    async def next_button(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't control this player!", ephemeral=True)
            return
        if self.ctx.voice_client:
            await next(self.ctx)
            await self.update_embed(self.ctx.voice_client.source.station)  # Update the embed with the current station info
        else:
            await interaction.response.send_message("Bot is not connected to a voice channel!", ephemeral=True)
        await self.update_embed(self.ctx.voice_client.source.station)  # Update the embed with the current station info
        await interaction.response.defer()  # Acknowledge the interaction without sending a message

    @discord.ui.button(label="⏹", style=ButtonStyle.danger)
    async def stop_button(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't control this player!", ephemeral=True)
            return
        if self.ctx.voice_client:
            self.ctx.voice_client.stop()
            await interaction.response.defer()  # Acknowledge the interaction without sending a message
            await interaction.response.send_message("⏹ Stopped the radio stream.", ephemeral=True)
        else:
            await interaction.response.send_message("No audio is playing right now!", ephemeral=True)

    # Volume control button
    @discord.ui.button(label="🔉", style=ButtonStyle.secondary, row=1)
    async def decrease_volume_button(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't control this player!", ephemeral=True)
            return
        if self.ctx.voice_client:
            current_volume = self.ctx.voice_client.source.volume * 100
            new_volume = max(current_volume - 10, 0)  # Decrease volume by 10, min 0
            self.ctx.voice_client.source.volume = new_volume / 100
            await self.update_embed(self.ctx.voice_client.source.station)  # Update the embed with the current station info
            await interaction.response.send_message(f"Volume decreased to {int(new_volume)}%", ephemeral=True)
            await interaction.response.defer()  # Acknowledge the interaction without sending a message   
        else:
            await interaction.response.send_message("No audio is playing right now!", ephemeral=True)

    @discord.ui.button(label="🔊", style=ButtonStyle.secondary, row=1)
    async def increase_volume_button(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't control this player!", ephemeral=True)
            return
        if self.ctx.voice_client:
            current_volume = self.ctx.voice_client.source.volume * 100
            new_volume = min(current_volume + 10, 200)  # Increase volume by 10, max 200
            self.ctx.voice_client.source.volume = new_volume / 100
            await self.update_embed(self.ctx.voice_client.source.station)  # Update the embed with the current station info
            await interaction.response.send_message(f"Volume increased to {int(new_volume)}%", ephemeral=True)
            await interaction.response.defer()  # Acknowledge the interaction without sending a message            
        else:
            await interaction.response.send_message("No audio is playing right now!", ephemeral=True)
            

# ==========================================================================================================================
                                            ### PLAYING LOCAL AUDIO ###
# ==========================================================================================================================
# Playing local audio 
@bot.command()
async def play(ctx):
    # Check if the user is in a voice channel
    if ctx.author.voice:
        channel = ctx.author.voice.channel

        # If bot is not connected, join the channel
        if not ctx.voice_client:
            await channel.connect()

        # Play the audio
        source = FFmpegPCMAudio("Rick.mp3")
        ctx.voice_client.play(source)
        await ctx.send(f"Now playing {source}")
    else:
        await ctx.send("You need to be in a voice channel first!")

# ==========================================================================================================================
                                            ### RADIO STREAM BY URL ###
# ==========================================================================================================================
# Playing Radio by URL
@bot.command()
async def radiourl(ctx, url: str, volume: float = 0.6):
    """
    Play a radio stream in the user's voice channel.
        - url: The direct stream URL.
        - volume: Optional, default is 0.5 (50%).
    """
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        # Join if not connected
        if not ctx.voice_client:
            await channel.connect()
        # FFmpeg options for reconnecting to unstable streams
        """
            before_options:
                - These options are applied before the actual input URL is processed
                - mainly used to configure the connection behavior
                
                -reconnect 1:
                    - Tells FFmpeg to try reconnecting automatically if the stream drops.
                    - Without this, the bot would stop if the radio server briefly disconnects.
                -reconnect_streamed 1:
                    - Ensures that even for streams that FFmpeg thinks are “live” (streamed media), it will attempt to reconnect.
                    - Important for live radio streams that FFmpeg treats as “endless” streams.
                -reconnect_delay_max 5:
                    - Sets the maximum delay (in seconds) before trying to reconnect.
                    - Here, FFmpeg will wait up to 5 seconds between reconnect attempts.
            
            options:
                - These options are applied after the input URL is processed, usually controlling the decoding or playback.

                -vn (Video None):
                    - It tells FFmpeg ignore any video streams and only process the audio.
                    - Most radio streams don’t have video, but adding this ensures FFmpeg doesn’t waste resources or throw errors if a stream has a tiny video track embedded.
        """
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'    # No video
        }
        # Attempt to play the radio stream
        try:
            source = FFmpegPCMAudio(url, **ffmpeg_options)  # FFmpegPCMAudio(url, before_options=before_options, options=options)
            player = PCMVolumeTransformer(source, volume=volume)    # Adjust the volume on the fly
            ctx.voice_client.stop()
            ctx.voice_client.play(player)
            # Create an embed message
            embed = discord.Embed(
                title = "▶ Now Playing",
                description= f"**Radio Stream**\nVolume: {int(volume * 100)}%",
                color = 0x00ffcc
            )
            embed.set_thumbnail(url=img_url)
            embed.set_author(name="Mr. Radio", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_footer(text=f"Use {prefix}help for more commands")

            await ctx.send(embed=embed, view=PlayerControls(ctx))
        except discord.ClientException:
            await ctx.send("Already playing a stream!")
        except Exception as e:
            await ctx.send(f"Failed to stream: {e}")
            if ctx.voice_client:
                await ctx.voice_client.disconnect() 
    else:
        await ctx.send("You need to be in a voice channel first!")

# ==========================================================================================================================
                                                ### RADIO STREAMING ###
# ==========================================================================================================================
                                                
RADIO_BROWSER_API = "https://de2.api.radio-browser.info/json"
# Store playlist for guild
radio_playlists = {}

# Search Radio Stations
async def search_station(search_type: str, query: str):
    url = f"{RADIO_BROWSER_API}/stations/by{search_type}/{query}?order=votes&reverse=true&limit=10"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            stations = await resp.json()
            return stations

# Play the current station
async def play_current_station(ctx):
    playlist = radio_playlists.get(ctx.guild.id)
    if not playlist:
        await ctx.send(f"No playlist found. Start with '{prefix}radio")
        return
    
    idx = playlist["index"]
    stations = playlist["stations"]    

    if idx < 0 or idx >= len(stations):
        await ctx.send("No more stations in the list.")
        return
    station = stations[idx]
    stream_url = station["url"]
    station_name = station["name"]

    # Play the radio station
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        if not ctx.voice_client:
            await channel.connect()

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        try:
            source = FFmpegPCMAudio(stream_url, **ffmpeg_options)
            player = PCMVolumeTransformer(source, volume=volume)
            player.station = station  # Attach the station info to the player object
            ctx.voice_client.stop()
            ctx.voice_client.play(player)

            # Create an embed message
            embed = discord.Embed(
                title = "▶ Now Playing",
                description= f"**{station_name}**\nIndex: {idx + 1}/{len(stations)}",
                color = 0x00ffcc
            )
            embed.set_thumbnail(url=station.get("favicon"))
            embed.set_author(name="Mr. Radio", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.add_field(name="Country", value=station.get("country", "Unknown"), inline=True)
            embed.add_field(name="Language", value=station.get("language", "Unknown").title(), inline=True)
            embed.add_field(name="Volume", value=f"{int(volume * 100)}%", inline=True)
            embed.set_footer(text=f"Use {prefix}help for more commands")                   

            view = PlayerControls(ctx, None)
            message = await ctx.send(embed=embed, view=view)  # Add player controls to the message
            view.message = message  # Store the message reference in the view for future updates
            await view.update_embed(station)  # Update the embed with the current station info
            
        except discord.ClientException:
            await ctx.send("Already playing a stream!")

        except Exception as e:
            await ctx.send(f"Failed to stream: {e}")
    else:
        await ctx.send("You must be in a voice channel to play a station")

# Search Radio Stations by name, country or tag
@bot.command()
async def radio(ctx, search_type: str, *, query: str):
    search_type = search_type.lower()
    if search_type not in ["name", "country", "tag", "language"]:
        await ctx.send("Invalid search type! Use name, country, language or tag.")
        return
    await ctx.send(f"🔍Searching for radio stations by {search_type}: {query}...")
    # Delete the message after 5 seconds of searching
    await ctx.message.delete(delay=5)

    stations = await search_station(search_type, query)
    if not stations:
        await ctx.send("Couldn't find a close match for your query.")
        return
    
    # Picking top 10 stations
    top_stations = stations[:10]

    # Saving the playlist for this guild
    radio_playlists[ctx.guild.id] = {"stations": top_stations, "index": 0}
    
    """
    await ctx.send("### 🎵 Found top 10 stations:\n" + "\n".join(
        [f"{i+1}. {s['name']}" for i, s in enumerate(top_stations)]
    ))
    """
    # Create an embed message for the stations
    embed = discord.Embed(
        title= f"🎵 Top {len(top_stations)} stations for '{query}'",
        color=0x1DB954
    )
    for i, station in enumerate(top_stations, start=1):
        name = station.get("name", "Unknown")
        country = station.get("country", "Unknown")
        language = station.get("language", "Unknown")
        embed.add_field(
            name=f"{i}. {name}", 
            value=f"Country: {country}\nLanguage: {language}", inline=True
        )
    embed.set_footer(text=f"Use {prefix}help for more commands")     
    await ctx.send(embed=embed)

    # Play the first station
    await play_current_station(ctx)


# Skip to the next radio station
@bot.command()
async def next(ctx):
    playlist = radio_playlists.get(ctx.guild.id)
    if not playlist:
        await ctx.send("No playlist to skip.")
        return
    
    playlist["index"] += 1
    await play_current_station(ctx)

# Go back to the previous radio station
@bot.command()
async def prev(ctx):
    playlist = radio_playlists.get(ctx.guild.id)
    if not playlist:
        await ctx.send("No playlist to go back")
        return
    
    playlist["index"] -= 1
    await play_current_station(ctx)

# Stop the radio station
@bot.command()
async def pause(ctx):
    if not ctx.voice_client.is_playing():
        await ctx.send("No audio is playing right now!")
        return
    await ctx.voice_client.pause()
    await ctx.send("⏸ Paused the radio stream.")

# Resume the radio station
@bot.command(name="resume")
async def resume(ctx):
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("▶️ Resumed playback.")
    else:
        await ctx.send("There's nothing paused right now.")

# Jump to a station in the playlist
@bot.command(name="jump")
async def jump(ctx, index: int):
    playlist = radio_playlists.get(ctx.guild.id)
    if not playlist:
        await ctx.send("No playlist found.")
        return    
    if index < 1 or index > len(playlist["stations"]):
        await ctx.send(f"Invalid station number.\nChoose between 1 and {len(playlist['stations'])}.")
        return    
    playlist["index"] = index - 1
    await play_current_station(ctx)

# Stop the current radio stream
@bot.command()
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏹ Stopped the radio stream.")
    else:
        await ctx.send("No audio is playing right now!")
        

bot.run(TOKEN)
