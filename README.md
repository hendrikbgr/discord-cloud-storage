Secure File Management System
=============================

Overview
--------

This project is a Flask-based web application designed for secure file management, including encryption, decryption, and storage functionalities. It leverages the Cryptodome library for cryptographic operations, SQLite for data storage, and integrates with Discord for file uploads. The application allows users to upload files, which are then split, encrypted, and stored securely. Files can be retrieved, decrypted, and downloaded through the web interface.

Features
--------

-   File upload and automatic encryption.
-   Secure file splitting and reassembling.
-   File encryption using AES with EAX mode for confidentiality and authenticity.
-   Secure storage of file metadata in a SQLite database.
-   File download with decryption.
-   Automated clean-up of temporary files.
-   Discord webhook integration for file upload notifications.

Requirements
------------

-   Python 3.x
-   Flask
-   Pycryptodome
-   SQLite3
-   PrettyTable
-   tqdm
-   requests
-   asyncio

Installation
------------

1.  Clone the repository to your local machine:

bashCopy code

`git clone https://github.com/hendrikbgr/discord-cloud-storage`

1.  Navigate into the project directory:

bashCopy code

`cd discord-cloud-storage`

1.  Install the required Python packages:

bashCopy code

`pip install -r requirements.txt`

Usage
-----

1.  Start the Flask application:

bashCopy code

`python app.py`

1.  Open your web browser and navigate to `http://localhost:5001`.

2.  Use the web interface to upload, manage, and download files.

Configuration
-------------

-   `DATABASE_FILE`: Path to the SQLite database file.
-   `WEBHOOK_URL`: Your Discord webhook URL for notifications.
-   `PREFIX`: Prefix for commands (if applicable).

Endpoints
---------

-   `/`: Main page for uploading and viewing files.
-   `/delete/<int:file_id>`: Delete a file entry from the database.
-   `/download/<int:file_id>`: Download and decrypt a file.

File Encryption and Decryption
------------------------------

Files are encrypted using AES with EAX mode for combined confidentiality and authenticity. Upon uploading, files are split into chunks, encrypted, and stored. For downloading, encrypted chunks are fetched, decrypted, and reassembled.

Discord Integration
-------------------

Files are uploaded to Discord through webhooks for ease of access and notification. Ensure your webhook URL is correctly configured in the `WEBHOOK_URL` variable.

Database Structure
------------------

The SQLite database stores file metadata, including names, sizes, chunk lists, and encryption keys. Ensure proper handling and security of this database to prevent unauthorized access.

Contributing
------------

Please feel free to contribute to the development of this project. Submit pull requests, report bugs, and suggest enhancements through the GitHub repository.

License
-------

[License type] - Please specify the license under which this project is released.
