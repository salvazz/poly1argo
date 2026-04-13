import os
import time
import requests
import subprocess
import threading
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
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"Error enviando telegram: {e}")

def check_process(name_pattern):
    """Verifica si un proceso existe de forma robusta en Linux y Windows."""
    try:
        if os.name == 'nt': # Windows
            output = subprocess.check_output(['tasklist', '/FI', f'IMAGENAME eq python.exe', '/FO', 'CSV']).decode(errors='ignore')
            return name_pattern.lower() in output.lower()
        else: # Linux
            output = subprocess.check_output(["pgrep", "-f", name_pattern]).decode(errors='ignore')
            return len(output.strip().splitlines()) > 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def start_agents():
    """Lanza los procesos de forma segura."""
    enviar_telegram("🚀 *Iniciando Agentes Argo...*")
    
    # Validar existencia de binarios
    p_path = os.path.join(BASE_DIR, PYTHON_PATH) if not PYTHON_PATH.startswith("/") else PYTHON_PATH
    s_path = os.path.join(BASE_DIR, STREAMLIT_PATH) if not STREAMLIT_PATH.startswith("/") else STREAMLIT_PATH
    
    # Usar shell=True solo para nohup en linux, de forma controlada
    if os.name != 'nt':
        subprocess.Popen(f"nohup {PYTHON_PATH} Argo_Motor_24x7.py > motor.log 2>&1 &", shell=True, cwd=BASE_DIR)
        subprocess.Popen(f"nohup {STREAMLIT_PATH} run Argo_Dashboard_Autonomo.py --server.port 8501 > dashboard.log 2>&1 &", shell=True, cwd=BASE_DIR)
    else:
        # En Windows usamos start /B
        subprocess.Popen(f"start /B python Argo_Motor_24x7.py", shell=True, cwd=BASE_DIR)
        subprocess.Popen(f"start /B streamlit run Argo_Dashboard_Autonomo.py --server.port 8501", shell=True, cwd=BASE_DIR)
        
    time.sleep(5)
    enviar_telegram(get_status_msg())

def get_status_msg():
    motor_ok = check_process("Argo_Motor_24x7.py")
    dashboard_ok = check_process("Argo_Dashboard_Autonomo.py")
    
    hb_status = "Desconocido"
    if os.path.exists(HEARTBEAT_FILE):
        try:
            with open(HEARTBEAT_FILE, "r") as f:
                last_hb = float(f.read().strip())
                diff = time.time() - last_hb
                if diff < 300:
                    hb_status = f"Activo (hace {int(diff)}s)"
                else:
                    hb_status = f"⚠ RETRASADO (hace {int(diff)}s)"
        except: hb_status = "Error lectura"
    
    msg = "📊 *ESTADO DE ARGO*\n\n"
    msg += f"🤖 Motor: {'✅ ONLINE' if motor_ok else '❌ OFFLINE'}\n"
    msg += f"🖥 Dashboard: {'✅ ONLINE' if dashboard_ok else '❌ OFFLINE'}\n"
    msg += f"💓 Heartbeat: {hb_status}"
    return msg

def poll_telegram():
    """Hilo dedicado para responder comandos de Telegram."""
    last_update_id = 0
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    print("Hilo de Telegram iniciado...")
    
    while True:
        try:
            r = requests.get(url, params={"offset": last_update_id + 1, "timeout": 20}, timeout=25)
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
                        enviar_telegram("Pong! 🏓 El Watchdog está vivo.")
        except Exception as e:
            print(f"Error en hilo Telegram: {e}")
        time.sleep(1)

def health_check_loop():
    """Hilo dedicado para monitorear la salud del sistema."""
    sent_alert = False
    print("Hilo de Monitoreo de Salud iniciado...")
    
    while True:
        try:
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
                
        except Exception as e:
            print(f"Error en hilo Salud: {e}")
            
        time.sleep(120) # Verificar cada 2 minutos

if __name__ == "__main__":
    # Lanzar hilos independientes para evitar bloqueos
    t_tele = threading.Thread(target=poll_telegram, daemon=True)
    t_health = threading.Thread(target=health_check_loop, daemon=True)
    
    t_tele.start()
    t_health.start()
    
    # Mantener el proceso principal vivo
    while True:
        time.sleep(1)
