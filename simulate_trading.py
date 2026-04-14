import random
import pandas as pd

# CONFIGURACIÓN DE LA SIMULACIÓN
capital_inicial = 50
operaciones_objetivo = 300
historial = []
saldo_actual = capital_inicial
VENTAJA_IA_EDGE = 0.05  # 5% de Edge relativo sobre el precio del mercado

print(
    f"Iniciando simulacion de {operaciones_objetivo} operaciones con capital inicial de ${capital_inicial}..."
)

for i in range(1, operaciones_objetivo + 1):
    # 1. El Investigador encuentra una cuota (precio del mercado entre 0.15 y 0.85)
    cuota = round(random.uniform(0.15, 0.85), 2)

    # Protección ante división por cero o cuota inválida
    if cuota <= 0:
        continue

    # 2. La IA estima la probabilidad real (P_real = cuota * (1 + edge))
    # Solo operamos si detectamos valor esperado positivo (Edge)
    p_estimada = cuota * (1 + VENTAJA_IA_EDGE)

    # 3. El Gestor de Riesgos decide invertir el 5% del saldo actual
    monto_apuesta = round(saldo_actual * 0.05, 2)

    # 4. Simulación del resultado basado en la probabilidad real del mercado (cuota)
    exito = random.random() < cuota

    if exito:
        beneficio = monto_apuesta * (1 / cuota - 1)
        saldo_actual += beneficio
        resultado = "GANADA"
    else:
        saldo_actual -= monto_apuesta
        resultado = "PERDIDA"

    # Guardar en el historial
    historial.append(
        {
            "Operacion": i,  # Evitamos caracteres especiales por seguridad de encoding
            "Cuota": cuota,
            "Inversion": monto_apuesta,
            "Resultado": resultado,
            "Saldo Final": round(saldo_actual, 2),
        }
    )

    # Si nos quedamos sin dinero, paramos
    if saldo_actual <= 0:
        print(f"Bancarrota en la operacion {i}!")
        break

# MOSTRAR RESULTADOS
df_resultados = pd.DataFrame(historial)
print("Resultado de la Simulacion de 300 Trades")
print(df_resultados.tail(10))  # Mostramos las últimas 10

ganancia_total = saldo_actual - capital_inicial
print(
    f"Simulacion terminada. Saldo final: ${round(saldo_actual, 2)} (Ganancia: ${round(ganancia_total, 2)})"
)

# Exportar con encoding explícito
df_resultados.to_csv("Simulacion_Resultados.csv", index=False, encoding="utf-8")
