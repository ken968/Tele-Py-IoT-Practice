from sensor import payload
from http.client import EXPECTATION_FAILED
from dotenv import load_dotenv
import os
import paho.mqtt.client as mqtt
import json
import time
import requests
import psycopg2

load_dotenv()
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

DB_CONFIG = {
    "host": "localhost",
    "port": 8812,
    "user": "admin",
    "password": "quest",
    "database": "qdb"
}

last_update_id = 0
last_temp = 0

def stats_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        query = "SELECT max(suhu), min(suhu) FROM data_sensor;"
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result
    except Exception as e:
        print(f"Error DB: {e}")
        return None

def kirim_tele(pesan, keyboard=None):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": pesan,
            "parse_mode": "Markdown"
        }
        if keyboard:
            payload["reply_markup"] = json.dumps(keyboard)

        response = requests.post(url, data=payload, timeout=5)
        response.raise_for_status()
    except Exception as e:
        print(f"....Telegram Error: {e}")

def Perintah_tele():
    global last_update_id
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}"
    
    menu = {
        "keyboard": [
            [{"text": "Status Terakhir"}, {"text": "Statistik"}],
            [{'text': "fan ON"}, {"text": "fan OFF"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

    try:
        response = requests.get(url).json()
        for update in response.get("result", []):
            last_update_id = update["update_id"]
            message_text = update["message"]["text"]
            if message_text == "/status":
                status_msg = f"Suhu terakhir: {last_temp}°C"
                kirim_tele(status_msg)
                print(f"membalas perintah /status: {last_temp}C")

            elif message_text == "/stats":
                max_t, min_t = stats_db()
                if max_t is not None:
                    msg = (f"Statistik semua data:\n"
                            f"Max suhu: {max_t}°C\n"
                            f"Min suhu: {min_t}°C")
                    kirim_tele(msg)
                    print(f"membalas perintah /stats: {msg}")
                else:
                    kirim_tele("Tidak ada data untuk dihitung")
                    print("Tidak ada data untuk dihitung")
                
    except Exception as e:
        print(f"Error Telegram Polling: {e}")

def catatan_db(pesan, nilai_suhu):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        query = f"INSERT INTO alarm_history (ts, pesan, suhu_overheat) VALUES (systimestamp(), '{pesan}', {nilai_suhu});"
        cur.execute(query)
        conn.commit()
        cur.close()
        conn.close()
        print(f"Data berhasil disimpan ke database: {pesan} - {nilai_suhu}°C")
    except Exception as e:
        print(f"Error DB: {e}")
    finally:
        if conn:
            conn.close()    

def on_message(client, userdata, msg):
    global last_temp
    try:
        data = json.loads(msg.payload.decode())
        suhu = data.get("suhu")
        last_temp = suhu

        if last_temp is None:
            return

        if suhu > 30:
            print(f"Suhu terlalu panas ({last_temp}°C)")
            catatan_db("Suhu terlalu panas", last_temp)
            client.publish("device/kipas", "on")
            print("nyalakan fan")
        else:
            print(f"Suhu normal ({last_temp}°C)")
            client.publish("device/kipas", "off")
    except json.JSONDecodeError:
        print('Error: Format data dari mqtt bukan json valid')
    except Exception as e:
        print(f"Error MQTT: {e}")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Disconnected with result code " + str(rc))
        print("Mencoba menyambung kembali...")
        try:
            client.reconnect()
        except Exception as e:
            print(f"Gagal reconnect: {e}")

def on_connect(client, userdata, flags, rc, property):
    if rc == 0:
        print("Terhubung ke MQTT Broker dengan sukses")
        client.subscribe("sensor/dht22")
    else:
        print(f"Gagal terhubung ke MQTT Broker dengan kode: {rc}")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect("localhost", 1883)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.loop_start()

print("Tele command aktif")

try:
    while True:
        Perintah_tele()
        time.sleep(1)
except KeyboardInterrupt:
    print("program dihentikan")