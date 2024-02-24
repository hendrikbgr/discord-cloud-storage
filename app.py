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
import env
import re
import platform


app = Flask(__name__)
app.secret_key = os.urandom(16)

DATABASE_FILE = env.DATABASE_FILE
WEBHOOK_URL = env.WEBHOOK_URL
PREFIX = '!'

FILE_PATH_SEP = '\\' if platform.system() == 'Windows' else '/'

def create_path(*args):
    """Create a file path suitable for the current operating system."""
    return FILE_PATH_SEP.join(args)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            file_path = create_path('temp_upload', file.filename)
            file.save(file_path)
            asyncio.run(process_file(file_path))
            # Delete all files in temp_chunks and temp_upload after processing
            shutil.rmtree(create_path('temp_chunks'), ignore_errors=True)
            shutil.rmtree(create_path('temp_upload'), ignore_errors=True)
            os.makedirs(create_path('temp_chunks'))
            os.makedirs(create_path('temp_upload'))

    files_info = asyncio.run(fetch_file_information())
    return render_template('index.html', files_info=files_info)

def convert_bytes(byte_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if byte_size < 1024.0:
            break
        byte_size /= 1024.0
    return f"{byte_size:.2f} {unit}"

def numerical_sort_key(filename):
    """Extracts numerical part of the filename and returns it as an integer."""
    numbers = re.findall(r'\d+', filename)
    return int(numbers[0]) if numbers else 0

def decrypt_and_reassemble(chunk_filenames, output_file, key_hex):
    key = bytes.fromhex(key_hex)
    chunks = []

    # Sort files by the numerical part of their names
    for chunk_filename in sorted(chunk_filenames, key=numerical_sort_key):
        with open(chunk_filename, 'rb') as chunk_file:
            nonce = chunk_file.read(16)
            tag = chunk_file.read(16)
            ciphertext = chunk_file.read()

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

def download_chunk(chunk_data):
    i, chunk_url = chunk_data  # Unpack the tuple to get the index and URL
    response = requests.get(chunk_url)
    if response.status_code == 200:
        chunk_filename = f'temp_chunks/chunk_{i + 1}.enc'  # Use index in filename for clarity
        with open(chunk_filename, 'wb') as chunk_file:
            chunk_file.write(response.content)
        return (i, chunk_filename)  # Return a tuple of the index and filename
    else:
        print(f"Failed to download chunk {i + 1} from {chunk_url}")
        return (i, None)  # Return the index and None if download failed

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
    indexed_chunks_urls = list(enumerate(chunks_urls))
    downloaded_chunks = [None] * len(chunks_urls)  # Preallocate list with placeholders

    total_chunks = len(chunks_urls)  # Total number of chunks to download

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor, tqdm(total=total_chunks, desc='Downloading chunks', unit='chunk') as progress_bar:  # Adjust number of workers as necessary
        future_to_index = {executor.submit(download_chunk, (i, url)): i for i, url in indexed_chunks_urls}

        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                if result[1]:  # Check if the download was successful
                    downloaded_chunks[index] = result
            except Exception as exc:
                print(f'Chunk download generated an exception: {exc}')
            finally:
                progress_bar.update(1)  # Update the progress bar

    # Filter out None values in case some downloads failed
    downloaded_chunks = [chunk for chunk in downloaded_chunks if chunk is not None]

    # Continue with file reassembly and decryption
    try:
        print(f"Key from database: {key_hex}")
        decrypt_and_reassemble([chunk for index, chunk in sorted(downloaded_chunks)], file_name, key_hex)
        conn.close()
        decrypted_file_path = os.path.join(os.getcwd(), 'temp_download', file_name)

        @after_this_request
        def cleanup(response):
            shutil.rmtree('temp_chunks', ignore_errors=True)
            shutil.rmtree('temp_download', ignore_errors=True)
            os.makedirs('temp_chunks', exist_ok=True)  # Modified line
            os.makedirs('temp_download', exist_ok=True)  # Modified line
            return response
        return send_file(decrypted_file_path, as_attachment=True)

    except Exception as e:
        print(f"Error during decryption: {e}")
        conn.close()
        shutil.rmtree('temp_chunks', ignore_errors=True)
        shutil.rmtree('temp_download', ignore_errors=True)
        os.makedirs('temp_chunks', exist_ok=True)  # Modified line
        os.makedirs('temp_download', exist_ok=True)  # Modified line
        return "Decryption failed", 500


    

def upload_to_discord(output_directory):
    print("Uploading chunks to Discord...")
    chunks_paths = [os.path.join(output_directory, filename) for filename in sorted(os.listdir(output_directory), key=lambda f: int(re.search(r'(\d+)', f).group())) if filename.endswith('.enc')]

    indexed_chunk_paths = [(i, path) for i, path in enumerate(chunks_paths)]
    chunks_urls = [None] * len(chunks_paths)  # Preallocate list with None to maintain order

    total_chunks = len(chunks_paths)  # Total number of chunks for the progress bar
    max_retries = 5  # Set maximum number of retries for each chunk

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor, tqdm(total=total_chunks, desc='Uploading chunks', unit='chunk') as progress_bar:
        # Initial upload attempts
        future_to_index = {executor.submit(upload_chunk, path): index for index, path in indexed_chunk_paths}

        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            retries = 0
            while retries < max_retries:
                try:
                    chunk_url = future.result()
                    if chunk_url:
                        chunks_urls[index] = chunk_url  # Assign URL to correct position based on original index
                        break  # Exit retry loop if upload was successful
                except Exception as exc:
                    print(f'Chunk upload generated an exception: {exc}')
                    retries += 1
                    if retries < max_retries:
                        print(f"Retrying upload for chunk {index + 1}, attempt {retries + 1}")
                        # Re-submit the failed upload task
                        future = executor.submit(upload_chunk, indexed_chunk_paths[index][1])
                finally:
                    progress_bar.update(1)

    # Check if there are any chunks that failed all retries and handle them as needed
    if None in chunks_urls:
        print("Some chunks failed to upload after multiple attempts.")
        # You can add additional error handling here, such as raising an exception or notifying the user.

    return chunks_urls



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

def upload_chunk(chunk_path, max_retries=5):
    retry_count = 0
    while retry_count < max_retries:
        try:
            with open(chunk_path, 'rb') as file:
                response = send_file_to_discord(file.read())
                if response.status_code == 200:  # Check if request was successful
                    attachment_cdn_url = response.json()['attachments'][0]['url']
                    return attachment_cdn_url
                else:
                    raise Exception(f"Upload failed with status code: {response.status_code}")
        except Exception as e:
            print(f"Error sending file: {e}, retrying...")
            retry_count += 1
            time.sleep(1)  # Wait a second before retrying to avoid hitting rate limits
    return None




def send_file_to_discord(file_content):
    files = {'file': ('test.enc', file_content)}
    data = {'content': 'File Upload'}
    response = requests.post(WEBHOOK_URL, files=files, data=data)
    return response



def save_to_database(input_file, chunks_urls, key_hex):
    file_size = os.path.getsize(input_file)
    print(f'File size: {file_size} bytes')
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
