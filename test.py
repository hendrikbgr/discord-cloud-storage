import discord
from discord.ext import commands
import sys

# Replace 'YOUR_BOT_TOKEN' with your actual bot token
TOKEN = 'MTE3ODY2MTI2MjQxOTMwODU5NQ.G40YBm.iVjb7DGIdEpKMPMfGflVAXjGGkJR9uFz-vEOFA'
PREFIX = '!'
intents = discord.Intents.default()
intents.messages = True  # Enable the message intent

channel_id = sys.argv[1]
message = sys.argv[2]

print('1')
# Create an instance of the bot
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

print('2')
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

print('3')
@bot.event
async def on_message(message):
    # Ignore messages from the bot itself to avoid an infinite loop
    if message.author == bot.user:
        return

    await bot.process_commands(message)

print('4')
@bot.command(name='send_message')
async def send_message(ctx, channel_id, *, message):
    try:
        # Convert the channel_id to an integer
        channel_id = int(channel_id)
        
        # Get the channel object using the channel_id
        channel = bot.get_channel(channel_id)
        
        if channel:
            # Send the message to the specified channel
            await channel.send(message)
            await ctx.send(f'Message sent to channel {channel_id}')
        else:
            await ctx.send(f'Channel with ID {channel_id} not found.')
    except ValueError:
        await ctx.send('Invalid channel ID. Please provide a valid integer.')



# Get the channel ID and message from command-line arguments

print('5')
# Run the bot with the token
bot.run(TOKEN)
print('6')
