import sys
import os
import json
from unittest.mock import patch
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv(os.path.join(os.getcwd(), ".env"))

# Fix encoding para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# Asegurarse de que el directorio actual está en el path para importar módulos locales
sys.path.append(os.getcwd())

import Argo_Motor_24x7

def run_high_volatility_test():
    print("[TEST] Iniciando Test de Alta Volatilidad con Cerebro Bayesiano...")
    print("----------------------------------------------------------")
    
    # ERROR 1: Proteger exposición de API Key
    key = os.environ.get('GROQ_API_KEY')
    key_display = key[:10] if (key and isinstance(key, str)) else 'NO ENCONTRADA'
    print(f"Usando Groq Key (Prefijo): {key_display}...")
    
    # ERROR 2: Mocking robusto usando patch
    def mock_obtener_alta_vol():
        # Simulamos un mercado de alto volumen para forzar la lógica
        return [{
            "titulo": "Test Mercado Volatil",
            "volumen": 150000,
            "precio": 0.50,
            "volatilidad": 0.25
        }]
    
    print("Inyectando mercado de simulación de alto volumen...")
    
    # Aplicamos el parche de forma que afecte a todas las referencias en Argo_Motor_24x7
    with patch('Argo_Motor_24x7.obtener_datos_polymarket', side_effect=mock_obtener_alta_vol):
        print("Analizando mercado inyectado...")
        try:
            Argo_Motor_24x7.ejecutar_mision_compra()
        except Exception as e:
            print(f"Error durante la ejecucion: {e}")
        
    print("----------------------------------------------------------")
    print("Test finalizado.")

if __name__ == "__main__":
    run_high_volatility_test()
