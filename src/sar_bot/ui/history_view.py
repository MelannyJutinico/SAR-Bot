"""Consulta de registros y pasos; ningun calculo de reglas."""
from pathlib import Path

OUTCOMES = {"success": "Exito", "destroyed": "Destruccion", "time_limit": "Limite temporal"}
STRATEGIES = {"shortest": "Ruta corta", "thermal": "Ruta segura (calor)", "random": "Movimientos al azar", "dqn": "Red neuronal"}

def draw_history(app):
    app.card((28,112,1224,718))
    app.text("HISTORIAL Y TRAZAS",(52,137),22,bold=True)
    app.text("Ultimas 20 misiones / 10000 estados. Exporta para conservar fuera de memoria.",(52,177),13)
    if app.history_files is not None:
        app.text("Importar JSON desde outputs/mission_traces",(52,215),16)
        for local,name in enumerate(app.history_files[app.history_file_page*6:app.history_file_page*6+6]):
            index=app.history_file_page*6+local
            app.button(f"history_import_{index}",name,(52,260+local*62,1150,44))
        app.button("history_files_prev","Anterior",(52,650,180,36))
        app.button("history_files_next","Siguiente",(260,650,180,36))
        app.button("history_files_close","Volver al historial",(900,745,328,40))
    else:
        app.text(f"Registradas: {len(app.history.records)} | pendientes: {len(app.history.pending)}",(52,211),13)
        app.history_page=min(app.history_page,max(0,(len(app.history.records)-1)//5))
        for local,record in enumerate(app.history.records[app.history_page*5:app.history_page*5+5]):
            index=app.history_page*5+local;y=248+local*78
            app.button(f"history_select_{index}",f"{index+1}. {STRATEGIES[record.strategy]} / {OUTCOMES.get(record.metrics['outcome'],record.metrics['outcome'])}",(52,y,350,38))
            app.text(record.episode.scenario.name[:40],(52,y+44),12)
        app.button("history_prev","Anterior",(52,650,160,34))
        app.button("history_next","Siguiente",(235,650,167,34))
        record=app.history_selected
        if record:
            app.text("Configuracion: "+record.episode.configuration_id,(440,213),12)
            app.text("Escenario: "+record.episode.scenario_id,(440,239),12)
            metrics=record.metrics
            app.text(f"{STRATEGIES[record.strategy]} | semilla {record.seed} | {OUTCOMES.get(metrics['outcome'],metrics['outcome'])} | rescates {metrics['rescued']}",(440,275),15)
            app.text(f"Pasos {metrics['steps']} | dano {metrics['damage_total']} / robots {metrics['damage_by_robot']}",(440,306),14)
            model=(Path(record.model).parent.name+"/"+Path(record.model).name) if record.model else "No aplica"
            app.wrap("Modelo: "+model+" | hash: "+(record.episode.checkpoint_sha256 or "no registrado"),440,336,770,12)
            app.text("EVENTOS (personas y robots numerados desde 1)",(440,395),14,bold=True)
            for i,event in enumerate(record.events[app.history_event_page*6:app.history_event_page*6+6]):
                value=event.value+1 if event.kind in ("recogida","entrega") and isinstance(event.value,int) else event.value
                app.text(f"Paso {event.step}: {event.kind} | robot {event.robot or '-'} | {value if value is not None else ''}",(440,426+i*25),13)
            app.button("history_events_prev","Eventos anteriores",(440,586,240,32))
            app.button("history_events_next","Eventos siguientes",(710,586,240,32))
            step=min(app.history_step,len(record.episode.states)-1);state=record.episode.states[step]
            action=record.episode.actions[step-1] if step else "inicio"
            app.text(f"TRAZA: paso {step} | accion conjunta previa {action} | entregadas {sorted(state.rescued)}",(440,635),13)
            for i,robot in enumerate(state.robots):
                app.text(f"R{i+1}: {robot.position} | carga {robot.carrying} (ID desde 0) | dano {robot.damage} | integridad {robot.integrity}",(440,660+i*22),12)
            app.button("history_step_prev","Paso anterior",(440,710,240,32))
            app.button("history_step_next","Paso siguiente",(710,710,240,32))
        else:
            app.wrap("Selecciona una mision registrada o importa una traza. Los calculos de comparacion completados tambien se registran.",440,280,730,17)
        app.button("history_files","Importar traza",(52,751,220,38))
        app.button("history_export","Exportar seleccion",(300,751,245,38),enabled=record is not None)
        app.button("history_replay","Reproducir desde cero",(575,751,300,38),enabled=record is not None)
        app.button("history_close","Volver a analisis",(900,751,328,38))
    app.text(app.history.message[:170],(52,804),12)
