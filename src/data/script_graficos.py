import pandas as pd
import matplotlib.pyplot as plt
import os

# =========================================================
# 1. CARGA Y PREPARACIÓN DE DATOS
# =========================================================
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_file = os.path.join(script_dir, "..", "data", "resultados_fase.csv")

# Leer el CSV asegurando que usa el punto y coma
df = pd.read_csv(csv_file, delimiter=';')

# Convertir las comas decimales (europeas) a puntos (Python) y pasar a números
cols_numericas = ['P_Informed', 'Exito', 'Tiempo_Segundos', 'N_att_Medio', 'V_x_Media_cm_s', 'M_Medio_Orden']
for col in cols_numericas:
    if df[col].dtype == object:
        df[col] = df[col].str.replace(',', '.').astype(float)

# Agrupar los 10 intentos haciendo la media
resultados = df.groupby('P_Informed').agg(
    Probabilidad_Exito=('Exito', 'mean'),
    Tiempo_Medio=('Tiempo_Segundos', 'mean'),
    Velocidad_Media=('V_x_Media_cm_s', 'mean'),
    Orden_M=('M_Medio_Orden', 'mean')
).reset_index()

print("--- RESUMEN DE LA TRANSICIÓN DE FASE ---")
print(resultados.to_string(index=False))

# =========================================================
# 2. ESTILO GRÁFICO PARA EL TFG
# =========================================================
# Estilo limpio y académico
plt.style.use('bmh')
color_exito = '#2ca02c'
color_vel = '#1f77b4'
color_orden = '#d62728'

# =========================================================
# 3. GENERACIÓN DE GRÁFICAS
# =========================================================

# --- GRÁFICA 1: Probabilidad de Éxito ---
plt.figure(figsize=(8, 5))
plt.plot(resultados['P_Informed'], resultados['Probabilidad_Exito'], 
         marker='o', markersize=8, linewidth=2.5, color=color_exito)
plt.title('Transición de Fase: Capacidad de Resolución', fontsize=14, pad=15)
plt.xlabel('Fracción de Hormigas Informadas ($p_{informed}$)', fontsize=12)
plt.ylabel('Probabilidad de Éxito', fontsize=12)
plt.ylim(-0.05, 1.05)
plt.axvline(x=0.55, color='gray', linestyle='--', alpha=0.5, label='Umbral de Transición')
plt.legend()
plt.tight_layout()
ruta_g1 = os.path.join(script_dir, "..", "data", "grafica_exito.png")
plt.savefig(ruta_g1, dpi=300)
plt.close()

# --- GRÁFICA 2: Velocidad Macroscópica ---
plt.figure(figsize=(8, 5))
plt.plot(resultados['P_Informed'], resultados['Velocidad_Media'], 
         marker='s', markersize=8, linewidth=2.5, color=color_vel)
plt.title('Dinámica del Enjambre: Velocidad de Avance', fontsize=14, pad=15)
plt.xlabel('Fracción de Hormigas Informadas ($p_{informed}$)', fontsize=12)
plt.ylabel('Velocidad Media en el eje X (cm/s)', fontsize=12)
plt.tight_layout()
ruta_g2 = os.path.join(script_dir, "..", "data", "grafica_velocidad.png")
plt.savefig(ruta_g2, dpi=300)
plt.close()

# --- GRÁFICA 3: Parámetro de Orden M(t) ---
plt.figure(figsize=(8, 5))
plt.plot(resultados['P_Informed'], resultados['Orden_M'], 
         marker='D', markersize=8, linewidth=2.5, color=color_orden)
plt.title('Emergencia del Orden Geométrico $M(t)$', fontsize=14, pad=15)
plt.xlabel('Fracción de Hormigas Informadas ($p_{informed}$)', fontsize=12)
plt.ylabel('Parámetro de Orden', fontsize=12)
# Añadimos una nota explicando el límite geométrico
plt.text(0.05, 0.32, 'Límite máximo por\nrestricción anatómica (52º)', fontsize=10, color='dimgray')
plt.tight_layout()
ruta_g3 = os.path.join(script_dir, "..", "data", "grafica_orden.png")
plt.savefig(ruta_g3, dpi=300)
plt.close()

print("\n¡Gráficas generadas con éxito!")
print(f"Guardadas en: {os.path.join(script_dir, '..', 'data')}")