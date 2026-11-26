"""Tabla de resultados reales, sin clasificacion automatica de ganadores."""
from pathlib import Path

def draw_comparison(app):
    from .app import scenario_label
    comparison = app.comparison_for_display
    request = comparison.request
    scenario = request.scenario
    app.card((28,112,1224,718))
    app.text("COMPARACION DE ESTRATEGIAS",(52,137),22,bold=True)
    if scenario.configuration_id != app.scenario.configuration_id:
        app.text("Configuracion anterior; la preparacion actual es diferente.",(690,145),14)
    if app.comparison and app.last_comparison and app.comparison.request != app.last_comparison.request:
        app.button("comparison_current" if app.comparison_show_saved else "comparison_saved",
                   "Ver calculo vigente" if app.comparison_show_saved else "Ver ultima completa",(930,180,298,30))
    app.text(scenario_label(scenario),(52,177),16)
    app.text("Las cuatro estrategias intentan el mismo rescate, cada una desde el inicio.",(52,211),15)
    app.text("Compara primero personas entregadas; después pasos y daño. No se entrena aquí.",(52,237),14)
    app.text(f"{scenario.victim_count} personas · Mismo mapa, calor y posiciones · Azar reproducible: {request.seed}",(52,268),14)
    labels=("Estrategia / estado", "Rescates", "Finalizacion", "Pasos", "Dano total")
    xs=(52,330,450,660,770)
    for x,label in zip(xs,labels): app.text(label,(x,310),15,bold=True)
    names={"dqn":"Red neuronal","shortest":"Ruta corta","thermal":"Ruta segura (calor)","random":"Movimientos al azar"}
    statuses={"pending":"Calculando","completed":"Lista","failed":"Error al ejecutar","incompatible":"No disponible"}
    outcomes={"success":"Rescate completo","destroyed":"Robot destruido","time_limit":"Tiempo agotado"}
    for i,row in enumerate(comparison.rows.values()):
        y=350+i*88
        app.text(names[row.strategy]+" / "+statuses[row.status],(52,y),14)
        if row.metrics:
            rescued,outcome,steps,damage=row.metrics
            for x,value in zip(xs[1:],(f"{rescued}/{scenario.victim_count}",outcomes.get(outcome,outcome),steps,damage)):
                app.text(str(value),(x,y),15)
            app.button("replay_"+row.strategy,"Ver recorrido",(1040,y-5,185,34))
        if row.error: app.wrap(row.error,52,y+28,1120,12)
        else:
            descriptions={"dqn":"Decisiones de una red entrenada; usa el modelo base guardado.",
                          "shortest":"Prioriza distancia; no considera el calor.",
                          "thermal":"Considera distancia y daño térmico al planificar.",
                          "random":"Acciones al azar; referencia básica para comparar."}
            app.text(descriptions[row.strategy],(52,y+29),12)
    app.text("Pasos = tiempo simulado. Menos dano en un fracaso no implica una estrategia mejor.",(52,713),14)
    app.button("comparison_export","Exportar CSV",(52,751,240,38),enabled=not comparison.futures and app.export_future is None)
    if app.last_result is not None:
        app.button("comparison_individual","Última misión terminada",(330,751,250,38))
    app.button("history","Historial",(620,751,240,38))
    app.button("view_preparation","Volver a preparacion",(900,751,328,38))
    app.text(app.comparison_message or "Modelo base fijo; comparar y reproducir no entrenan. Mismas condiciones iniciales.",(52,802),12)
