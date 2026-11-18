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
    app.text("PREPARACION", (900,137),18,bold=True)
    app.text("Plantilla de desarrollo",(900,174),12)
    app.button("scenario",app.scenario.name.replace("_"," ")[:32],(900,194,328,42))
    from .app import STRATEGIES
    app.text("Estrategia",(900,257),12)
    app.button("strategy",STRATEGIES[app.strategy_index][1],(900,277,328,42))
    app.button("models","Seleccionar modelo DQN",(900,335,328,38))
    entry=app.selected_model()
    if entry:
        app.wrap(f"{entry.path.parent.name}: {entry.status}",900,385,320,14)
    if STRATEGIES[app.strategy_index][0]=="dqn":
        app.wrap(app.model_problem() or "Perfil compatible; modelo piloto, sin garantia de rescate.",900,437,320,14)
    app.button("edit","Editar personas",(900,505,328,40),enabled=app.scenario.victim_count==3)
    app.button("save_file","Guardar",(900,565,155,36))
    app.button("load_file","Cargar personal",(1070,565,158,36))
    app.button("prepare","Validar y preparar",(900,625,328,40),primary=True)
    app.button("view_execution","Ver ejecucion",(900,680,328,38))
    app.button("compare","Comparar estrategias",(900,730,328,36))
    app.wrap(notice(app),900,775,320,12)


def draw_execution(app):
    app.text("EJECUCION",(900,137),18,bold=True)
    from .app import STRATEGIES
    app.wrap("Estrategia: "+(app.request.strategy if app.comparison_replaying and app.request else STRATEGIES[app.strategy_index][1]),900,185,320)
    if app.request and app.request.model:
        from pathlib import Path
        app.wrap("Modelo: "+Path(app.request.model).parent.name+" (piloto)",900,235,320,14)
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
               "Estrategia: "+result.strategy,"Semilla aleatoria: "+(str(result.seed) if result.strategy=="random" else "No aplica"),
               "Certificacion: "+str(result.certification)]
        for i,line in enumerate(lines):app.text(line,(900,255+i*28),14)
        from pathlib import Path
        model=Path(result.model).parent.name+" (piloto)" if result.model else "No aplica"
        app.wrap("Modelo: "+model,900,470,320,14)
        app.wrap("Escenario: "+result.scenario_name.replace("_"," "),900,520,320,13)
        app.text("ID fisico:",(900,575),12)
        app.text(result.scenario_id[:32],(900,597),12);app.text(result.scenario_id[32:],(900,615),12)
        app.text("ID configuracion exacta:",(900,647),12)
        app.text(result.configuration_id[:32],(900,669),12);app.text(result.configuration_id[32:],(900,687),12)
    app.button("history","Historial y trazas",(900,706,328,34))
    app.button("view_preparation","Volver a preparacion",(900,750,328,40))
    if app.comparison_for_display:
        app.button("comparison_table","Ver comparacion",(900,799,328,32))
    else:
        app.text("Ultima mision finalizada; no se recalcula.",(900,799),12)


def draw_models(app):
    app.text("MODELOS DQN",(900,137),18,bold=True)
    app.wrap(f"Perfil actual: {app.scenario.width}x{app.scenario.height}, {app.scenario.victim_count} personas",900,177,320,14)
    for local,entry in enumerate(app.models[app.model_page*4:app.model_page*4+4]):
        i=app.model_page*4+local
        y=225+local*108
        reason=entry.reason(app.scenario)
        app.button(f"model_{i}",entry.path.parent.name+(" · piloto" if not entry.error else " · invalido"),
                   (900,y,328,36),enabled=reason is None)
        description=reason or f"{entry.dimensions[0]}x{entry.dimensions[1]} / {entry.dimensions[2]} personas / {entry.mode} / {entry.observation_size}"
        app.wrap(description,900,y+39,320,12)
        if not reason:app.text(entry.architecture+" / "+entry.schema,(900,y+75),11)
    app.button("models_prev","Anterior",(900,660,155,30),enabled=app.model_page>0)
    app.button("models_next","Siguiente",(1070,660,158,30),enabled=(app.model_page+1)*4<len(app.models))
    app.wrap(app.model_problem() or "Compatible no equivale a validado.",900,695,320,13)
    app.button("models_close","Volver",(900,770,328,38))
