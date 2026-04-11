import streamlit as st
import requests
import pandas as pd
import os
import random


# 1. Función para conectar con la API de Polymarket
def obtener_mercados_vivos():
    url = "https://polymarket.com"
    try:
        response = requests.get(url)
        data = response.json()
        mercados = []
        for event in data:
            mercados.append(
                {
                    "Evento": event.get("title", "N/A"),
                    "Volumen ($)": f"{float(event.get('volume', 0)):,.2f}",
                    "Categoría": event.get("category", "N/A"),
                }
            )
        return pd.DataFrame(mercados)
    except:
        return pd.DataFrame([{"Error": "No se pudo conectar con la API"}])


# 2. Configuración Visual
st.set_page_config(page_title="Argo Dashboard", layout="wide")
st.title("🚢 Argo: Centro de Control de Inversión")

# Columnas: Izquierda (Agentes) | Derecha (Mercados en vivo)
col1, col2 = st.columns([2, 1])

with col1:
    st.header("🤖 Análisis de la Tripulación")
    if st.button("🚀 Iniciar Misión de Agentes"):
        st.write("Ejecutando Investigador, Gestor y Crítico...")
        # Aquí llamarías a: argo_flota_blindada.kickoff()
        st.success("Informe generado con éxito.")
        st.info("Resumen: Recomendación de $2.50 en 'Elecciones 2028'")

        # Simulación de 300 trades
        import random
        import pandas as pd

        # CONFIGURACIÓN DE LA SIMULACIÓN
        capital_inicial = 50
        operaciones_objetivo = 300
        historial = []
        saldo_actual = capital_inicial

        st.write(f"🚀 Iniciando simulación de {operaciones_objetivo} operaciones...")

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
                st.write(f"⚠️ ¡Bancarrota en la operación {i}!")
                break

        # MOSTRAR RESULTADOS
        df_resultados = pd.DataFrame(historial)
        st.write("### 📊 Resultado de la Simulación de 300 Trades")
        st.line_chart(df_resultados["Saldo Final"])
        st.dataframe(df_resultados.tail(10))  # Mostramos las últimas 10

        ganancia_total = saldo_actual - capital_inicial
        st.write(
            f"✅ Simulación terminada. Saldo final: ${round(saldo_actual, 2)} (Ganancia: ${round(ganancia_total, 2)})"
        )

    if st.button("🚀 Iniciar Simulación 2.0 (Estrategia Selectiva)"):
        st.write("Ejecutando Simulación 2.0 con filtro de valor...")

        # CONFIGURACIÓN 2.0 (Estrategia Profesional)
        capital_inicial = 50
        operaciones_objetivo = 300
        historial_2 = []
        saldo_actual = capital_inicial

        st.write(f"🚀 Iniciando Simulación 2.0 con Filtro de Valor...")

        for i in range(1, operaciones_objetivo + 1):
            # 1. El mercado ofrece una cuota
            cuota_mercado = round(random.uniform(0.20, 0.80), 2)
            prob_mercado = cuota_mercado  # Simplificamos: cuota 0.50 = 50%

            # 2. La IA analiza y encuentra una probabilidad REAL (Ventaja estratégica)
            # Solo entramos si nuestra IA detecta un error de cuota de al menos el 10%
            ventaja_ia = random.uniform(0.05, 0.15)
            prob_ia = prob_mercado + ventaja_ia

            # FILTRO DEL CRÍTICO: ¿Hay valor suficiente?
            if prob_ia > (
                prob_mercado * 1.15
            ):  # Exigimos un 15% de ventaja sobre el mercado
                # 3. GESTOR DE RIESGOS: Kelly dinámico (Invertimos según la confianza)
                # Si hay mucha ventaja, subimos al 8%. Si hay poca, bajamos al 2%
                porcentaje_inversion = 0.02 if ventaja_ia < 0.10 else 0.07
                monto_apuesta = round(saldo_actual * porcentaje_inversion, 2)

                # 4. EJECUCIÓN
                exito = random.random() < prob_ia

                if exito:
                    # En Polymarket, si compras a 0.50 y ganas, recibes 1.00 (doblas)
                    # Ganancia = Monto * (1 / Cuota - 1)
                    beneficio = monto_apuesta * (1 / cuota_mercado - 1)
                    saldo_actual += beneficio
                    resultado = "GANADA"
                else:
                    saldo_actual -= monto_apuesta
                    resultado = "PERDIDA"

                historial_2.append(
                    {
                        "Operación": i,
                        "Ventaja %": round(ventaja_ia * 100, 2),
                        "Inversión": monto_apuesta,
                        "Resultado": resultado,
                        "Saldo Final": round(saldo_actual, 2),
                    }
                )

            if saldo_actual <= 0:
                st.write(f"⚠️ Bancarrota en la op {i}")
                break

        # MOSTRAR RESULTADOS 2.0
        df_2 = pd.DataFrame(historial_2)
        st.write(f"### 📈 Resultado Simulación 2.0 (Estrategia Selectiva)")
        st.line_chart(df_2["Saldo Final"])
        st.write(f"Operaciones realizadas (con filtro): {len(df_2)} de 300 analizadas")

        ganancia_neta = saldo_actual - capital_inicial
        st.write(
            f"✅ Finalizado. Saldo: ${round(saldo_actual, 2)} | Ganancia: ${round(ganancia_neta, 2)}"
        )

with col2:
    st.header("📊 Mercados en Vivo")
    st.write("Datos reales de Polymarket")
    df_mercados = obtener_mercados_vivos()
    st.table(df_mercados)  # Muestra la tabla con datos frescos

# Barra lateral para el capital
st.sidebar.header("💰 Billetera Phantom")
capital_base = st.sidebar.number_input("Saldo ($)", value=50)
