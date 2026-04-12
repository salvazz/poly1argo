import random
import pandas as pd

# CONFIGURACIÓN DE LA SIMULACIÓN
capital_inicial = 50
operaciones_objetivo = 300
historial = []
saldo_actual = capital_inicial

print(
    f"Iniciando simulacion de {operaciones_objetivo} operaciones con capital inicial de ${capital_inicial}..."
)

for i in range(1, operaciones_objetivo + 1):
    # 1. El Investigador encuentra una cuota (entre 0.10 y 0.90)
    cuota = round(random.uniform(0.15, 0.85), 2)

    # 2. El Gestor de Riesgos decide invertir el 5% (tu regla de los $2.50)
    monto_apuesta = round(saldo_actual * 0.05, 2)

    # 3. El Crítico evalúa (Simulamos un acierto basado en la cuota + ventaja de IA)
    # Suponemos que nuestra IA tiene un 5% de ventaja sobre el mercado
    probabilidad_exito = cuota + 0.05
    exito = random.random() < probabilidad_exito

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
            "Operación": i,
            "Cuota": cuota,
            "Inversión": monto_apuesta,
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
