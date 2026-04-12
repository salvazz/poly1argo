import sys
import os
import json

# Set environment variables BEFORE importing crewai or argo
from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), ".env"))

# Fix encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# Asegurarse de que el directorio actual está en el path
sys.path.append(os.getcwd())

import Argo_Motor_24x7

def run_high_volatility_test():
    print("[TEST] Iniciando Test de Alta Volatilidad con Cerebro Bayesiano...")
    print("----------------------------------------------------------")
    print(f"Usando Groq Key: {os.environ.get('GROQ_API_KEY')[:10]}...")
    
    # Sobrescribir el filtro de mercados
    original_obtener = Argo_Motor_24x7.obtener_datos_polymarket
    
    def obtener_alta_vol():
        mercados = original_obtener()
        res = [m for m in mercados if m.get('volumen', 0) > 100000]
        return res[:1] # Solo 1 para el test rápido
    
    Argo_Motor_24x7.obtener_datos_polymarket = obtener_alta_vol
    
    print("Analizando mercado de alto volumen...")
    try:
        Argo_Motor_24x7.ejecutar_mision_compra()
    except Exception as e:
        print(f"Error durante la ejecucion: {e}")
        
    print("----------------------------------------------------------")
    print("Test finalizado.")

if __name__ == "__main__":
    run_high_volatility_test()
