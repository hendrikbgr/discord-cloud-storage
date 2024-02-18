from flask import Flask, render_template, request, send_file, redirect, url_for, after_this_request, flash, get_flashed_messages
from Cryptodome.Cipher import AES 
from Cryptodome.Random import get_random_bytes
import os
import sqlite3
from datetime import datetime
from prettytable import PrettyTable
from tqdm import tqdm
import requests
import concurrent.futures
import asyncio
import time
import json
import shutil


app = Flask(__name__)
app.secret_key = os.urandom(16)

DATABASE_FILE = 'file_data.db'
WEBHOOK_URL = 'https://discord.com/api/webhooks/1178788710800707655/XdM-0ESGAsMUXgN-ORy3oUWRuc6Ukd7DOjE1YQcr8qxsk-qCcW9AbVMQPX8_hBGLQySr'
PREFIX = '!'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            file_path = 'temp_upload/' + file.filename
            file.save(file_path)
            asyncio.run(process_file(file_path))
            # Delete all files in temp_chunks and temp_upload after processing
            shutil.rmtree('temp_chunks', ignore_errors=True)
            shutil.rmtree('temp_upload', ignore_errors=True)
            os.makedirs('temp_chunks')
            os.makedirs('temp_upload')

    files_info = asyncio.run(fetch_file_information())


    return render_template('index.html',files_info=files_info)

def convert_bytes(byte_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if byte_size < 1024.0:
            break
        byte_size /= 1024.0
    return f"{byte_size:.2f} {unit}"

def decrypt_and_reassemble(chunk_filenames, output_file, key_hex):
    key = bytes.fromhex(key_hex)
    print("Key:", key)
    chunks = []

    for chunk_filename in sorted(chunk_filenames):
        with open(chunk_filename, 'rb') as chunk_file:
            nonce = chunk_file.read(16)
            tag = chunk_file.read(16)
            ciphertext = chunk_file.read()

        print("Nonce:", nonce)
        print("Tag:", tag)

        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
        try:
            decrypted_chunk = cipher.decrypt_and_verify(ciphertext, tag)
            chunks.append(decrypted_chunk)
        except ValueError as e:
            print(f"Error during decryption: {e}")

    output_file_path = os.path.join('temp_download', output_file)

    with open(output_file_path, 'wb') as output_file:
        for chunk in chunks:
            output_file.write(chunk)

    print(f'Successfully decrypted and reassembled chunks into {output_file_path}.')





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

@app.route('/delete/<int:file_id>', methods=['GET'])
def delete_file_entry(file_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM files WHERE id=?", (file_id,))
    conn.commit()
    conn.close()
    flash('Deleted file from Database', 'success')
    return redirect(url_for('index'))

@app.route('/download/<int:file_id>', methods=['GET'])
def download_and_decrypt(file_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT file_name, chunk_list, key_hex FROM files WHERE id=?", (file_id,))
    result = cursor.fetchone()

    if not result:
        print(f"No entry found with ID {file_id}")
        conn.close()
        return "File not found", 404

    file_name, chunk_list, key_hex = result

    chunks_urls = chunk_list.split(', ')

    num_threads = request.args.get('num_threads', default=4, type=int)

    # Using ThreadPoolExecutor for concurrent downloading
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        downloaded_chunks = list(tqdm(executor.map(download_chunk, enumerate(chunks_urls)), desc='Downloading chunks', unit='chunk'))

    try:
        print(f"Key from database: {key_hex}")
        decrypt_and_reassemble(downloaded_chunks, file_name, key_hex)
        conn.close()
        decrypted_file_path = os.path.join(os.getcwd(), 'temp_download', file_name)

        @after_this_request
        def cleanup(response):
            shutil.rmtree('temp_chunks', ignore_errors=True)
            shutil.rmtree('temp_download', ignore_errors=True)
            os.makedirs('temp_chunks')
            os.makedirs('temp_download')
            return response
        return send_file(decrypted_file_path, as_attachment=True)

    except Exception as e:
        print(f"Error during decryption: {e}")
        conn.close()
        shutil.rmtree('temp_chunks', ignore_errors=True)
        shutil.rmtree('temp_download', ignore_errors=True)
        os.makedirs('temp_chunks')
        os.makedirs('temp_download')
        return "Decryption failed", 500
    

def download_chunk(chunk_data):
    i, chunk_url = chunk_data
    response = requests.get(chunk_url)
    if response.status_code == 200:
        chunk_filename = f'temp_chunks/chunk_{i + 1}.enc'
        with open(chunk_filename, 'wb') as chunk_file:
            chunk_file.write(response.content)
        return chunk_filename
    else:
        print(f"Failed to download chunk {i + 1} from {chunk_url}")
        return None


async def process_file(file_path):
    input_file = file_path
    output_directory = 'temp_chunks'

    key = get_random_bytes(16)
    key_hex = key.hex()

    split_and_encrypt(input_file, output_directory, key)

    chunks_urls = upload_to_discord(output_directory)

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

        # Save nonce and tag along with ciphertext
        nonce = cipher.nonce
        chunk_filename = os.path.join(output_directory, f'chunk_{i + 1}.enc')
        with open(chunk_filename, 'wb') as chunk_file:
            chunk_file.write(nonce)
            chunk_file.write(tag)
            chunk_file.write(ciphertext)

    print(f'Successfully split and encrypted {input_file} into {num_chunks} chunks.')

def upload_chunk(chunk_path):
    try:
        with open(chunk_path, 'rb') as file:
            response = send_file_to_discord(file.read())
        attachment_cdn_url = response.json()['attachments'][0]['url']
        return attachment_cdn_url
    except Exception as e:
        print(f"Error sending file: {e}")
        return None

def upload_to_discord(output_directory):
    chunks_paths = [os.path.join(output_directory, filename) for filename in sorted(os.listdir(output_directory)) if filename.endswith('.enc')]
    
    chunks_urls = []
    num_threads = 4  # Or any other number you deem appropriate

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        for chunk_url in tqdm(executor.map(upload_chunk, chunks_paths), desc='Uploading chunks', unit='chunk'):
            if chunk_url:
                chunks_urls.append(chunk_url)

    return chunks_urls

def send_file_to_discord(file_content):
    files = {'file': ('file.enc', file_content)}
    data = {'content': 'File Upload'}
    response = requests.post(WEBHOOK_URL, files=files, data=data)
    return response



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
    app.run(host='0.0.0.0', port=5001, debug=True)
