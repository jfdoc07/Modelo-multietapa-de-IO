import pulp

def resolver_planeacion_multietapa():
    # ==========================================
    # 1. DEFINICIÓN DE DIMENSIONES Y PARÁMETROS
    # ==========================================
    T_periodos = 4       # Número de periodos (t) [Ej: 4 trimestres del artículo]
    M_etapas = 4         # Número de etapas de proceso (i) [1, 2, 3, M]
    
    # Número de fuentes (máquinas) disponibles por cada etapa (j)
    # Etapa 1: 3 fuentes, Etapa 2: 2 fuentes, Etapa 3: 3 fuentes, Etapa 4: 4 fuentes
    J_fuentes = {1: 3, 2: 2, 3: 3, 4: 4}

    # Demanda requerida de producto terminado en cada periodo (d_t)[cite: 2]
    demanda = {
        1: 50500,
        2: 65500,
        3: 82000,
        4: 92000
    }

    # Condiciones iniciales y finales para el producto terminado (Etapa M)[cite: 4]
    I_plus_inicial = 1000  # Inventario inicial (K1)
    I_plus_final = 1000    # Inventario final deseado (K2)
    I_minus_inicial = 0    # Escasez inicial
    I_minus_final = 0      # Escasez final deseada

    # Costo de penalización por escasez (Psi)[cite: 3]
    psi_escasez = 4.0

    # Diccionarios de Costos y Capacidades (Se pueden poblar con datos reales de las tablas del paper)
    costo_produccion = {}
    costo_setup = {}
    capacidad = {}
    costo_inventario_proceso = {}
    costo_inventario_final = {}

    # Generación de datos de ejemplo basados en la estructura del artículo[cite: 3]
    for i in range(1, M_etapas + 1):
        for j in range(1, J_fuentes[i] + 1):
            for t in range(1, T_periodos + 1):
                # Costos base simulados acordes a la magnitud del caso de estudio
                costo_produccion[(i, j, t)] = 20.0 + (i * 5) + (j * 2)
                costo_setup[(i, j, t)] = 20000.0 + (i * 1000)
                capacidad[(i, j, t)] = 150000.0  # Capacidad amplia por fuente

    for i in range(1, M_etapas):
        for t in range(1, T_periodos + 1):
            costo_inventario_proceso[(i, t)] = 2.0  # Costo de mantener inventario en proceso[cite: 3]

    for t in range(1, T_periodos + 1):
        costo_inventario_final[(t)] = 3.0  # Costo de mantener producto terminado[cite: 3]


    # ==========================================
    # 2. INICIALIZACIÓN DEL MODELO DE OPTIMIZACIÓN
    # ==========================================
    modelo = pulp.LpProblem("Planeacion_Agregada_Multietapa_Multifuente", pulp.LpMinimize)


    # ==========================================
    # 3. VARIABLES DE DECISIÓN
    # ==========================================
    # X_ijt: Cantidad a producir (Entera >= 0)[cite: 2, 6]
    X = modelo.add_variable_dicts("X",
                                  ((i, j, t) for i in range(1, M_etapas + 1)
                                             for j in range(1, J_fuentes[i] + 1)
                                             for t in range(1, T_periodos + 1)),
                                  lowBound=0, cat='Integer')

    # Y_ijt: Variable binaria de alistamiento / setup (0 o 1)
    Y = modelo.add_variable_dicts("Y",
                                  ((i, j, t) for i in range(1, M_etapas + 1)
                                             for j in range(1, J_fuentes[i] + 1)
                                             for t in range(1, T_periodos + 1)),
                                  cat='Binary')

    # I_it: Inventario en proceso, etapas 1 a M-1
    I_proceso = modelo.add_variable_dicts("I_proceso",
                                          ((i, t) for i in range(1, M_etapas)
                                                  for t in range(0, T_periodos + 1)),
                                          lowBound=0, cat='Integer')

    # I_plus_t: Inventario de producto terminado
    I_plus = modelo.add_variable_dicts("I_plus", (t for t in range(0, T_periodos + 1)), lowBound=0, cat='Integer')

    # I_minus_t: Escasez de producto terminado
    I_minus = modelo.add_variable_dicts("I_minus", (t for t in range(0, T_periodos + 1)), lowBound=0, cat='Integer')

    # ==========================================
    # 4. FUNCIÓN OBJETIVO (Minimizar Costos Totales)[cite: 3]
    # ==========================================
    modelo += (
        # Costos de producción y alistamiento (setup)[cite: 3]
        pulp.lpSum(costo_produccion[i, j, t] * X[i, j, t] + costo_setup[i, j, t] * Y[i, j, t] 
                   for i in range(1, M_etapas + 1) 
                   for j in range(1, J_fuentes[i] + 1) 
                   for t in range(1, T_periodos + 1)) +
        
        # Costos de mantenimiento de inventario en proceso[cite: 3]
        pulp.lpSum(costo_inventario_proceso[i, t] * I_proceso[i, t] 
                   for i in range(1, M_etapas) 
                   for t in range(1, T_periodos + 1)) +
        
        # Costo de mantenimiento de inventario de producto terminado[cite: 3]
        pulp.lpSum(costo_inventario_final[t] * I_plus[t] 
                   for t in range(1, T_periodos + 1)) +
        
        # Costos de penalización por escasez (backorders)[cite: 3]
        pulp.lpSum(psi_escasez * I_minus[t] 
                   for t in range(1, T_periodos + 1))
    )


    # ==========================================
    # 5. RESTRICCIONES DEL SISTEMA
    # ==========================================

    # A. Condiciones Iniciales y Finales fijas[cite: 4]
    modelo += I_plus[0] == I_plus_inicial
    modelo += I_plus[T_periodos] == I_plus_final
    modelo += I_minus[0] == I_minus_inicial
    modelo += I_minus[T_periodos] == I_minus_final

    for i in range(1, M_etapas):
        modelo += I_proceso[i, 0] == 0          # Inventario inicial en proceso = 0[cite: 4]
        modelo += I_proceso[i, T_periodos] == 0   # Inventario final en proceso = 0[cite: 4]

    # B. Restricción de Capacidad y Acople con Setup ($X_{ijt} \le Cd_{ijt} \cdot Y_{ijt}$)[cite: 4]
    for i in range(1, M_etapas + 1):
        for j in range(1, J_fuentes[i] + 1):
            for t in range(1, T_periodos + 1):
                modelo += X[i, j, t] <= capacidad[i, j, t] * Y[i, j, t]

    # C. Balance de Inventario para Etapas Intermedias ($i = 1, \dots, M-1$)[cite: 4]
    for i in range(1, M_etapas):
        for t in range(1, T_periodos + 1):
            inv_anterior = I_proceso[i, t-1]
            produccion_actual = pulp.lpSum(X[i, j, t] for j in range(1, J_fuentes[i] + 1))
            consumo_siguiente = pulp.lpSum(X[i + 1, j, t] for j in range(1, J_fuentes[i + 1] + 1))
            
            modelo += produccion_actual + inv_anterior - consumo_siguiente - I_proceso[i, t] == 0

    # D. Balance para la Etapa Final ($M$) y Cumplimiento de Demanda[cite: 4]
    for t in range(1, T_periodos + 1):
        produccion_final = pulp.lpSum(X[M_etapas, j, t] for j in range(1, J_fuentes[M_etapas] + 1))
        modelo += (
            produccion_final + I_plus[t-1] - I_plus[t] + I_minus[t] - I_minus[t-1] == demanda[t]
        )


    # ==========================================
    # 6. EJECUCIÓN DEL SOLVER
    # ==========================================
    print("Resolviendo modelo de optimización...")
    stats = modelo.solve()

    # ==========================================
    # 7. REPORTE DE RESULTADOS
    # ==========================================
    print(f"\nEstado de la Solución: {stats.status_str}")
    print(f"Costo Total Mínimo Optimizado: ${pulp.value(modelo.objective):,.2f}\n")

    print("--- PLAN DE PRODUCCIÓN Y ESTADOS ÓPTIMOS ---")
    for t in range(1, T_periodos + 1):
        print(f"\n[ PERIODO {t} ] (Demanda del periodo: {demanda[t]} unids)")
        for i in range(1, M_etapas + 1):
            for j in range(1, J_fuentes[i] + 1):
                prod = X[i, j, t].varValue
                setup = Y[i, j, t].varValue
                if prod > 0 or setup == 1:
                    print(f"  -> Etapa {i}, Fuente {j}: Producir = {prod:,.0f} unids | Setup Activo (Y) = {int(setup)}")
        print(f"  -> Inventario Final de Producto Terminado (I+): {I_plus[t].varValue:,.0f}")
        print(f"  -> Escasez / Faltantes (I-): {I_minus[t].varValue:,.0f}")

if __name__ == "__main__":
    resolver_planeacion_multietapa()