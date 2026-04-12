import os
import time
import requests
import subprocess
import signal
from datetime import datetime
from dotenv import load_dotenv

# Configuración
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HEARTBEAT_FILE = os.path.join(BASE_DIR, "data", "motor_heartbeat.txt")

# Comandos de ejecución (ajustados a la ruta del servidor)
PYTHON_PATH = "./venv/bin/python3"
STREAMLIT_PATH = "./venv/bin/streamlit"

def enviar_telegram(mensaje):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"})

def check_process(name_pattern):
    try:
        output = subprocess.check_output(["pgrep", "-f", name_pattern])
        return len(output.strip().split()) > 0
    except:
        return False

def start_agents():
    enviar_telegram("🚀 *Iniciando Agentes Argo...*")
    # Iniciar Motor
    subprocess.Popen(f"nohup {PYTHON_PATH} Argo_Motor_24x7.py > motor.log 2>&1 &", shell=True, cwd=BASE_DIR)
    # Iniciar Dashboard
    subprocess.Popen(f"nohup {STREAMLIT_PATH} run Argo_Dashboard_Autonomo.py --server.port 8501 > dashboard.log 2>&1 &", shell=True, cwd=BASE_DIR)
    time.sleep(5)
    status = get_status_msg()
    enviar_telegram(status)

def get_status_msg():
    motor_ok = check_process("Argo_Motor_24x7.py")
    dashboard_ok = check_process("Argo_Dashboard_Autonomo.py")
    
    hb_status = "Desconocido"
    if os.path.exists(HEARTBEAT_FILE):
        with open(HEARTBEAT_FILE, "r") as f:
            last_hb = float(f.read().strip())
            diff = time.time() - last_hb
            if diff < 300:
                hb_status = f"Activo (hace {int(diff)}s)"
            else:
                hb_status = f"⚠ RETRASADO (hace {int(diff)}s)"
    
    msg = "📊 *ESTADO DE ARGO*\n\n"
    msg += f"🤖 Motor: {'✅ ONLINE' if motor_ok else '❌ OFFLINE'}\n"
    msg += f"🖥 Dashboard: {'✅ ONLINE' if dashboard_ok else '❌ OFFLINE'}\n"
    msg += f"💓 Heartbeat: {hb_status}"
    return msg

def poll_telegram():
    last_update_id = 0
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    
    while True:
        try:
            r = requests.get(url, params={"offset": last_update_id + 1, "timeout": 30})
            data = r.json()
            if data.get("ok"):
                for update in data.get("result", []):
                    last_update_id = update["update_id"]
                    msg = update.get("message", {})
                    text = msg.get("text", "")
                    sender_id = str(msg.get("from", {}).get("id", ""))
                    
                    if sender_id != str(CHAT_ID): continue # Solo responder al dueño
                    
                    if text == "/start":
                        start_agents()
                    elif text == "/status":
                        enviar_telegram(get_status_msg())
                    elif text == "/ping":
                        enviar_telegram("Pong! 🏓 El Watchdog está vivo.")
        except Exception as e:
            print(f"Error polling: {e}")
        time.sleep(1)

def watchdog_loop():
    sent_alert = False
    print("Watchdog iniciado...")
    
    # Iniciar el hilo de polling de telegram en el proceso principal o separado
    # Para simplicidad en un solo script, usaremos un loop que hace ambas cosas
    
    last_check_status = time.time()
    last_update_id = 0
    
    while True:
        try:
            # 1. Verificar Salud cada 2 minutos
            if time.time() - last_check_status > 120:
                motor_ok = check_process("Argo_Motor_24x7.py")
                hb_ok = False
                if os.path.exists(HEARTBEAT_FILE):
                    with open(HEARTBEAT_FILE, "r") as f:
                        last_hb = float(f.read().strip())
                        if time.time() - last_hb < 600: hb_ok = True
                
                if (not motor_ok or not hb_ok) and not sent_alert:
                    enviar_telegram("🚨 *ALERTA: Argo está caído o bloqueado!*\nUsa /status para verificar o /start para reiniciar.")
                    sent_alert = True
                elif motor_ok and hb_ok:
                    sent_alert = False
                
                last_check_status = time.time()

            # 2. Poll Telegram (Fast)
            r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", 
                             params={"offset": last_update_id + 1, "timeout": 10}, timeout=15)
            data = r.json()
            if data.get("ok"):
                for update in data.get("result", []):
                    last_update_id = update["update_id"]
                    msg = update.get("message", {})
                    text = msg.get("text", "").lower()
                    sender_id = str(msg.get("from", {}).get("id", ""))
                    
                    if sender_id != str(CHAT_ID): continue 
                    
                    if "/start" in text:
                        start_agents()
                    elif "/status" in text:
                        enviar_telegram(get_status_msg())
                    elif "/ping" in text:
                        enviar_telegram("Pong! 🏓")
        
        except Exception as e:
            print(f"Error principal loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    watchdog_loop()
