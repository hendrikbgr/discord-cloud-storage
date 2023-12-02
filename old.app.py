from flask import Flask, render_template, request, send_file
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import os
import sqlite3
import discord
from discord.ext import commands
from datetime import datetime
from flask_ngrok import run_with_ngrok  # ngrok is used to expose Flask app to the internet
from prettytable import PrettyTable  # Make sure to install this library using: pip install prettytable
from tqdm import tqdm
import requests
import asyncio  # Import asyncio module
import time

intents = discord.Intents.default()
intents.messages = True  # Enable the message intent

app = Flask(__name__)
run_with_ngrok(app)  # Start ngrok when app is run

TOKEN = 'MTE3ODY2MTI2MjQxOTMwODU5NQ.G40YBm.iVjb7DGIdEpKMPMfGflVAXjGGkJR9uFz-vEOFA'
DATABASE_FILE = 'file_data.db'
PREFIX = '!'

bot = commands.Bot(command_prefix=PREFIX, intents=intents)


# Global variable to store Flask app reference
flask_app = None



@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            file_path = 'temp_upload/' + file.filename
            file.save(file_path)
            asyncio.run(process_file(file_path, bot))

    files_info = asyncio.run(fetch_file_information())

    return render_template('index.html', files_info=files_info)

async def fetch_file_information():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, file_name, file_size, chunk_list FROM files")
    results = cursor.fetchall()
    conn.close()

    files_info = []
    for result in results:
        file_id, file_name, file_size, chunk_list = result
        chunk_amount = len(chunk_list.split(', '))
        formatted_size = convert_bytes(file_size)
        files_info.append({
            'id': file_id,
            'file_name': file_name,
            'formatted_size': formatted_size,
            'chunk_amount': chunk_amount
        })

    return files_info

@app.route('/download/<int:file_id>', methods=['GET'])
def download_and_decrypt(file_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT file_name, chunk_list, key_hex FROM files WHERE id=?", (file_id,))
    result = cursor.fetchone()

    if not result:
        print(f"No entry found with ID {file_id}")
        conn.close()
        return

    file_name, chunk_list, key_hex = result

    chunks_urls = chunk_list.split(', ')

    downloaded_chunks = []
    for i, chunk_url in enumerate(tqdm(chunks_urls, desc='Downloading chunks', unit='chunk')):
        response = requests.get(chunk_url)
        if response.status_code == 200:
            chunk_filename = f'temp_chunks/chunk_{i + 1}.enc'
            with open(chunk_filename, 'wb') as chunk_file:
                chunk_file.write(response.content)
            downloaded_chunks.append(chunk_filename)
        else:
            print(f"Failed to download chunk {i + 1} from {chunk_url}")

    decrypt_and_reassemble(downloaded_chunks, file_name, key_hex)

    conn.close()

    decrypted_file_path = os.path.join(os.getcwd(), 'temp_download', file_name)
    return send_file(decrypted_file_path, as_attachment=True)

def decrypt_and_reassemble(chunk_filenames, output_file, key_hex):
    key = bytes.fromhex(key_hex)
    print('key')
    chunks = []

    for chunk_filename in sorted(chunk_filenames):
        with open(chunk_filename, 'rb') as chunk_file:
            nonce = chunk_file.read(16)
            tag = chunk_file.read(16)
            ciphertext = chunk_file.read()

        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
        decrypted_chunk = cipher.decrypt_and_verify(ciphertext, tag)
        chunks.append(decrypted_chunk)

    output_file_path = os.path.join('temp_download', output_file)

    with open(output_file_path, 'wb') as output_file:
        for chunk in chunks:
            output_file.write(chunk)

    print(f'Successfully decrypted and reassembled chunks into {output_file_path}.')

def convert_bytes(byte_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if byte_size < 1024.0:
            break
        byte_size /= 1024.0
    return f"{byte_size:.2f} {unit}"

def list_and_download_files():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT id, file_name, file_size, chunk_list FROM files")
    results = cursor.fetchall()

    if not results:
        print("No files found in the database.")
    else:
        table = PrettyTable(['ID', 'File Name', 'File Size', 'Chunk Amount'])
        for result in results:
            file_id, file_name, file_size, chunk_list = result
            chunk_amount = len(chunk_list.split(', '))
            formatted_size = convert_bytes(file_size)
            table.add_row([file_id, file_name, formatted_size, chunk_amount])

        print(table)

        file_id_to_download = input("Enter the ID of the file you want to download (or 'cancel' to go back to the menu): ")

        if file_id_to_download.lower() != 'cancel':
            download_and_decrypt(file_id_to_download)

    conn.close()

async def process_file(file_path, bot):
    input_file = file_path
    output_directory = 'temp_chunks'

    key = get_random_bytes(16)
    key_hex = key.hex()

    split_and_encrypt(input_file, output_directory, key)

    chunks_urls = upload_to_discord(bot, output_directory)

    save_to_database(input_file, chunks_urls, key_hex)

def split_and_encrypt(input_file, output_directory, key):
    chunk_size = 23 * 1024 * 1024

    with open(input_file, 'rb') as file:
        data = file.read()

    num_chunks = (len(data) + chunk_size - 1) // chunk_size

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    for i in range(num_chunks):
        start = i * chunk_size
        end = (i + 1) * chunk_size
        chunk = data[start:end]

        cipher = AES.new(key, AES.MODE_EAX)
        ciphertext, tag = cipher.encrypt_and_digest(chunk)

        chunk_filename = os.path.join(output_directory, f'chunk_{i + 1}.enc')
        with open(chunk_filename, 'wb') as chunk_file:
            chunk_file.write(cipher.nonce)
            chunk_file.write(tag)
            chunk_file.write(ciphertext)

    print(f'Successfully split and encrypted {input_file} into {num_chunks} chunks.')

async def print_available_channels():
    await bot.wait_until_ready()
    print("Available Channels:")
    if not bot.guilds:
        print("Bot is not a member of any guilds.")
    else:
        for guild in bot.guilds:
            print(f"Guild: {guild.name}")
            for channel in guild.channels:
                print(f"{channel.name}: {channel.id}")

def upload_to_discord(bot, output_directory):
    chunks_urls = []

    channel_id = 1178676144782987295

    channel = bot.get_channel(channel_id)
    if not channel:
        print(f"Channel with ID {channel_id} not found.")
        return chunks_urls

    for filename in tqdm(sorted(os.listdir(output_directory)), desc='Uploading chunks', unit='chunk'):
        if filename.endswith('.enc'):
            chunk_path = os.path.join(output_directory, filename)
            with open(chunk_path, 'rb') as file:
                file_data = discord.File(file)
                try:
                    message = channel.send(file=file_data)
                    attachment_cdn_url = message.attachments[0].url if message.attachments else None
                    chunks_urls.append(attachment_cdn_url)
                except Exception as e:
                    print(f"Error sending file: {e}")

    return chunks_urls

def save_to_database(input_file, chunks_urls, key_hex):
    file_size = os.path.getsize(input_file)
    upload_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS files 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      file_name TEXT, 
                      chunk_list TEXT, 
                      key_hex TEXT, 
                      file_size INTEGER, 
                      upload_date TEXT)''')

    cursor.execute("INSERT INTO files (file_name, chunk_list, key_hex, file_size, upload_date) VALUES (?, ?, ?, ?, ?)",
                   (os.path.basename(input_file), ', '.join(chunks_urls), key_hex, file_size, upload_date))

    conn.commit()
    conn.close()

    print(f'Data saved to the database.')

if __name__ == '__main__':

    @bot.event
    async def on_ready():
        print(f'We have logged in as {bot.user}')
        await print_available_channels()

    bot.run(TOKEN)

    time.sleep(10)

    flask_app = app
    app.run(host='0.0.0.0', port=5000, debug=True)
