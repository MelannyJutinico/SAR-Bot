"""Presentacion de vistas: no simula, no evalua y no entrena."""
from dataclasses import dataclass


@dataclass(frozen=True)
class MissionResult:
    configuration_id: str
    scenario_id: str
    scenario_name: str
    strategy: str
    model: str | None
    seed: int
    outcome: str
    rescued: int
    total: int
    steps: int
    damage: tuple[int, int]
    temperatures: tuple[float, float]
    certification: str | None

    @classmethod
    def capture(cls, app):
        scenario, state, request = app.playback.episode.scenario, app.state, app.request
        return cls(scenario.configuration_id, scenario.scenario_id, scenario.name,
                   request.strategy, request.model, request.seed, state.outcome,
                   len(state.rescued), scenario.victim_count, state.steps,
                   tuple(r.damage for r in state.robots),
                   tuple(scenario.temperature_at(r.position) for r in state.robots),
                   app.validation_status)


def person_status(state, victim):
    if victim in state.rescued:
        return "Entregada en base"
    carrier = next((i + 1 for i,r in enumerate(state.robots) if r.carrying == victim), None)
    return f"Recogida: con robot {carrier}" if carrier else "Pendiente de recoger"


def notice(app):
    if app.learning_future or app.learning_active:
        return app.error or app.learning_message
    if app.file_message:
        return app.file_message
    if app.error:
        return app.error
    if app.comparison_replaying:
        return "Reproduccion de traza: sin decisiones, aprendizaje ni certificacion nueva."
    if app.future:
        return "Preparando y certificando en segundo plano..."
    if app.validation_status == "not_certified":
        return "No certificada: puedes explorar. No significa imposible."
    if app.validation_status == "certified":
        return "Certificada por referencia; DQN puede fallar en posiciones nuevas."
    return "Selecciona una configuracion y prepara la mision."


def draw_preparation(app):
    from .app import STRATEGIES, scenario_label
    app.text("PREPARAR RESCATE", (900,137),18,bold=True)
    app.text("Mapa del edificio",(900,174),12)
    app.button("scenario",scenario_label(app.scenario)[:35],(900,194,328,42))
    app.text("Elige el edificio y coloca a las personas.",(900,245),12)
    strategy, label, explanation = STRATEGIES[app.strategy_index]
    app.text("Cómo decidirán los robots",(900,274),12)
    app.button("strategy",label,(900,294,328,42))
    app.wrap(explanation,900,345,320,13)
    if strategy == "dqn":
        app.button("models","Elegir red neuronal",(900,405,328,34),enabled=not app.learning_future)
        app.button("mode_evaluate","Solo ejecutar",(900,456,158,34),
                   primary=not app.learning_active,enabled=not app.learning_future)
        app.button("mode_learn","Aprender",(1070,456,158,34),
                   primary=app.learning_active,enabled=not app.learning_future)
        detail = ("Guarda experiencias. Conserva nuevos pesos si no empeoran en los controles."
                  if app.learning_active else "Usa el modelo guardado sin modificarlo.")
        app.wrap(app.model_problem() or detail,900,502,320,12)
    else:
        app.wrap("Esta estrategia sigue reglas programadas. No necesita una red ni entrenamiento.",
                 900,414,320,13)
        app.wrap("Para entrenar, elige Red neuronal (DQN) en el selector de arriba.",
                 900,476,320,12)
    app.button("edit","Colocar personas",(900,551,328,36),enabled=app.scenario.victim_count==3 and not app.learning_future)
    app.button("save_file","Guardar mapa",(900,597,155,32))
    app.button("load_file","Mis mapas",(1070,597,158,32),enabled=not app.learning_future)
    app.button("prepare","Preparar nueva misión",(900,642,328,40),primary=True,enabled=not app.learning_future)
    app.button("view_execution","Ver misión y controles",(900,691,328,36))
    app.button("compare","Comparar las 4 estrategias",(900,737,328,36),enabled=not app.learning_future)
    app.wrap(notice(app),900,783,320,12)


def draw_execution(app):
    app.text("EJECUCION",(900,137),18,bold=True)
    mode = ("Aprender y guardar al finalizar" if app.request and app.request.learning
            else "Red guardada · sin actualizar pesos" if app.request and app.request.strategy == "dqn"
            else "Estrategia programada · sin entrenamiento")
    app.text(mode,(900,165),12)
    from .app import STRATEGIES
    labels = {key:label for key,label,_ in STRATEGIES}
    app.wrap("Estrategia: "+(labels[app.request.strategy] if app.comparison_replaying and app.request else STRATEGIES[app.strategy_index][1]),900,185,320)
    if app.request and app.request.model:
        from pathlib import Path
        app.wrap("Modelo base: "+Path(app.request.model).parent.name,900,235,320,14)
    app.wrap("Recoger no es entregar. El contador aumenta al llegar a la base.",900,290,320,14)
    label="Pausar" if app.playback and app.playback.playing else "Iniciar / continuar"
    app.button("play",label,(900,388,328,48),primary=True,enabled=app.playback is not None)
    app.button("step","Un paso",(900,448,158,40),enabled=app.playback is not None)
    app.button("reset","Reiniciar",(1070,448,158,40),enabled=app.playback is not None)
    app.text(f"Velocidad: {app.speed} pasos/s",(950,515),15)
    app.button("slower","-",(900,539,42,34));app.button("faster","+",(1186,539,42,34))
    app.switch("heat","Mapa de calor",app.show_heat,598)
    app.switch("paths","Recorridos",app.show_paths,638)
    app.button("view_analysis","Consultar resultado",(900,696,328,38))
    app.wrap(notice(app),900,746,320,13)
    app.text("ESPACIO Pausa / continua   N Paso",(900,801),12)


def draw_analysis(app):
    from .app import STRATEGIES
    app.text("ANALISIS",(900,137),18,bold=True)
    result=app.last_result
    if result is None:
        app.wrap("Todavia no hay una mision finalizada. Ejecuta una configuracion y consulta su resultado.",900,200,320)
    else:
        title={"success":"EXITO: rescate completo","destroyed":"FRACASO: robot destruido",
               "time_limit":"LIMITE DE TIEMPO"}.get(result.outcome,result.outcome)
        app.wrap(title,900,185,320,17)
        lines=[f"Entregadas: {result.rescued}/{result.total}",f"Pasos globales: {result.steps}",
               f"Dano R1 / R2: {result.damage[0]} / {result.damage[1]}",
               f"Temperatura final: {result.temperatures[0]:g} / {result.temperatures[1]:g} C",
               "Estrategia: "+dict((key,label) for key,label,_ in STRATEGIES)[result.strategy],
               "Azar reproducible: "+(str(result.seed) if result.strategy=="random" else "No aplica"),
               "Mapa: "+{"certified":"resoluble por una referencia", "not_certified":"sin rescate certificado"}.get(result.certification,"sin comprobar")]
        for i,line in enumerate(lines):app.text(line,(900,255+i*28),14)
        from pathlib import Path
        model=Path(result.model).parent.name if result.model else "No aplica"
        app.wrap("Modelo: "+model,900,470,320,14)
        app.wrap("Escenario: "+result.scenario_name.replace("_"," "),900,520,320,13)
        app.text("CÓMO LEER EL RESULTADO",(900,575),13,bold=True)
        app.wrap("Rescatar exige entregar en la base. Los pasos miden tiempo simulado; el daño suma la integridad perdida de ambos robots.",900,605,320,13)
        app.wrap("Un fracaso con poco daño no significa un mejor rescate.",900,674,320,12)
    app.button("history","Historial y trazas",(900,706,328,34))
    app.button("view_preparation","Volver a preparacion",(900,750,328,40))
    if app.comparison_for_display:
        app.button("comparison_table","Ver comparacion",(900,799,328,32))
    else:
        app.text("Ultima mision finalizada; no se recalcula.",(900,799),12)


def draw_models(app):
    from pathlib import Path
    app.text("ELEGIR RED NEURONAL",(900,137),18,bold=True)
    app.text(f"Mapa: {app.scenario.width} × {app.scenario.height} · {app.scenario.victim_count} personas",
             (900,177),14)
    app.text("Solo aparecen redes compatibles.",(900,205),12)
    entries = app.compatible_models()
    selected = Path(app.model_path).resolve() if app.model_path else None
    for local,(index,entry) in enumerate(entries[app.model_page*4:app.model_page*4+4]):
        y=245+local*100
        active = entry.path == selected
        name = "Red principal" if entry.status.startswith("congelado") else "Red experimental: " + entry.path.parent.name
        app.button(f"model_{index}",("En uso: " if active else "Usar: ")+name,
                   (900,y,328,36),primary=active)
        description = ("Modelo guardado para la presentación."
                       if entry.status.startswith("congelado") else "Experimento previo; puede rendir peor.")
        app.wrap(description,900,y+44,320,12)
    if not entries:
        app.wrap("No hay una red compatible. Elige Ruta corta o Ruta segura para ejecutar este mapa.",900,250,320,14)
        app.wrap(app.model_problem() or "",900,350,320,12)
    hidden=len(app.models)-len(entries)
    if len(entries)>4:
        app.button("models_prev","Anterior",(900,660,155,30),enabled=app.model_page>0)
        app.button("models_next","Siguiente",(1070,660,158,30),enabled=(app.model_page+1)*4<len(entries))
    if hidden:
        app.wrap(f"{hidden} redes de otros tamaños o no válidas están ocultas.",900,705,320,12)
    app.wrap("DQN es experimental: una red compatible también puede fallar en el rescate.",900,743,320,12)
    app.button("models_close","Volver a preparar",(900,787,328,30))
