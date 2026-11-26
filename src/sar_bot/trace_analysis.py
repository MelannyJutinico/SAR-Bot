"""Análisis observable de trazas conservadas (SARB-023).

Reproduce las acciones guardadas de un episodio en un motor nuevo y describe
solo lo que cambia en los estados: recogidas, entregas, tramos con daño,
rachas de movimientos bloqueados o de esperas, vaivenes y destrucción. No
atribuye intenciones al controlador. Los totales se comparan con la fila del
CSV para garantizar que la descripción corresponde al episodio publicado.

Las celdas se nombran como en la interfaz: columna en letra y fila en número,
con A1 en la esquina superior izquierda.
"""

from __future__ import annotations

import json
from pathlib import Path

from sar_bot.core import Scenario
from sar_bot.experiment import read_results, replay_actions, verify_results
from sar_bot.partitions import file_sha256
from sar_bot.report import STRATEGY_NAMES, _content_sha256, _table

ANALYSIS_SCHEMA = 1
WAIT = 4
STREAK = 5
OUTCOMES = {"success": "rescate completo", "destroyed": "robot destruido",
            "time_limit": "límite de pasos"}


def cell(position) -> str:
    x, y = position
    return f"{chr(ord('A') + x)}{y + 1}"


def episode_story(scenario: Scenario, actions) -> dict:
    """Desglose por robot y cronología de eventos observables de un episodio."""
    states = replay_actions(scenario, actions)
    count = len(states[0].robots)
    robots = [{"deliveries": 0, "waits": 0, "blocked": 0, "back_and_forth": 0, "hot_steps": 0,
               "damage": 0, "cells": {states[0].robots[i].position}} for i in range(count)]
    events, trips, pickups = [], [], {}
    heat = [None] * count
    blocked = [None] * count
    waiting = [None] * count

    def close(kind, i, end_step):
        if kind == "heat" and heat[i]:
            start, damage, hottest, cells = heat[i]
            where = "celda" if len(cells) == 1 else "celdas"
            if end_step == start:
                text = (f"Robot {i + 1} recibe {damage} de daño en el paso {start} "
                        f"({hottest:g} °C, {where} {', '.join(cells)})")
            else:
                text = (f"Robot {i + 1} recibe {damage} de daño entre los pasos {start} y "
                        f"{end_step} ({end_step - start + 1} pasos, hasta {hottest:g} °C, "
                        f"{where} {', '.join(cells)})")
            events.append((start, text))
            heat[i] = None
        if kind == "blocked" and blocked[i]:
            start, total, where = blocked[i]
            if total >= STREAK:
                events.append((start, f"Robot {i + 1} no logra moverse {total} veces seguidas "
                                      f"entre los pasos {start} y {end_step} (en {', '.join(where)})"))
            blocked[i] = None
        if kind == "wait" and waiting[i]:
            start, total, where = waiting[i]
            if total >= STREAK:
                events.append((start, f"Robot {i + 1} espera {total} pasos seguidos entre los "
                                      f"pasos {start} y {end_step} en {where}"))
            waiting[i] = None

    for index, (action, before, after) in enumerate(zip(actions, states, states[1:])):
        step = after.steps
        for i, robot_action in enumerate((action // 5, action % 5)):
            old, new, data = before.robots[i], after.robots[i], robots[i]
            data["cells"].add(new.position)
            if robot_action == WAIT:
                data["waits"] += 1
                close("blocked", i, step - 1)
                if waiting[i]:
                    waiting[i] = (waiting[i][0], waiting[i][1] + 1, waiting[i][2])
                else:
                    waiting[i] = (step, 1, cell(new.position))
            elif old.integrity > 0 and old.position == new.position:
                data["blocked"] += 1
                close("wait", i, step - 1)
                if blocked[i]:
                    start, total, where = blocked[i]
                    if cell(new.position) not in where:
                        where = where + [cell(new.position)]
                    blocked[i] = (start, total + 1, where)
                else:
                    blocked[i] = (step, 1, [cell(new.position)])
            else:
                close("blocked", i, step - 1)
                close("wait", i, step - 1)
            if (index >= 1 and new.position != old.position
                    and new.position == states[index - 1].robots[i].position):
                data["back_and_forth"] += 1
            delta = new.damage - old.damage
            if delta > 0:
                data["hot_steps"] += 1
                data["damage"] += delta
                temperature = scenario.temperature_at(new.position)
                if heat[i]:
                    start, damage, hottest, cells = heat[i]
                    if cell(new.position) not in cells:
                        cells = cells + [cell(new.position)]
                    heat[i] = (start, damage + delta, max(hottest, temperature), cells)
                else:
                    heat[i] = (step, delta, temperature, [cell(new.position)])
            else:
                close("heat", i, step - 1)
            if new.carrying is not None and old.carrying != new.carrying:
                pickups[new.carrying] = (i, step)
                events.append((step, f"Robot {i + 1} recoge a la persona {new.carrying + 1} en "
                                     f"{cell(new.position)}"))
            if old.integrity > 0 and new.integrity == 0:
                load = (f", cargando a la persona {old.carrying + 1}"
                        if old.carrying is not None else "")
                events.append((step, f"Robot {i + 1} queda destruido en {cell(new.position)} a "
                                     f"{scenario.temperature_at(new.position):g} °C{load}"))
        for victim in sorted(after.rescued - before.rescued):
            carrier = next(i for i, r in enumerate(before.robots) if r.carrying == victim)
            robots[carrier]["deliveries"] += 1
            start = pickups.get(victim, (carrier, None))[1]
            trips.append({"person": victim + 1, "robot": carrier + 1, "pickup": start,
                          "delivery": after.steps})
            events.append((after.steps, f"Robot {carrier + 1} entrega a la persona {victim + 1} "
                                        "en la base"))
    final = states[-1]
    for i in range(count):
        for kind in ("heat", "blocked", "wait"):
            close(kind, i, final.steps)
    pending = [v + 1 for v in range(scenario.victim_count)
               if v not in final.rescued and v not in {r.carrying for r in final.robots}]
    carried = [(i + 1, r.carrying + 1) for i, r in enumerate(final.robots) if r.carrying is not None]
    ending = f"Termina en el paso {final.steps}: {OUTCOMES.get(final.outcome, final.outcome)}"
    if carried:
        ending += "; " + ", ".join(f"robot {i} lleva a la persona {p}" for i, p in carried)
    if pending:
        ending += "; sin recoger: " + ", ".join(f"persona {p}" for p in pending)
    events.append((final.steps, ending))
    events.sort(key=lambda item: item[0])
    for i, robot in enumerate(final.robots):
        robots[i]["integrity"] = robot.integrity
        robots[i]["cells"] = len(robots[i]["cells"])
    return {"robots": robots, "trips": trips, "events": events, "outcome": final.outcome,
            "steps": final.steps, "rescued": len(final.rescued)}


def _check_against_row(story, row) -> list[str]:
    expected = {
        "steps": int(row["steps"]), "rescued": int(row["rescued"]), "outcome": row["outcome"],
        "waits": int(row["wait_actions"]), "blocked": int(row["blocked_moves"]),
        "damage": int(row["damage_total"]),
        "deliveries": (int(row["deliveries_robot_1"]), int(row["deliveries_robot_2"])),
    }
    observed = {
        "steps": story["steps"], "rescued": story["rescued"], "outcome": story["outcome"],
        "waits": sum(r["waits"] for r in story["robots"]),
        "blocked": sum(r["blocked"] for r in story["robots"]),
        "damage": sum(r["damage"] for r in story["robots"]),
        "deliveries": tuple(r["deliveries"] for r in story["robots"]),
    }
    return [f"{key}: CSV {expected[key]} y traza {observed[key]}"
            for key in expected if expected[key] != observed[key]]


def _select(rows, case):
    matches = [row for row in rows
               if row["scenario_path"] == case["scenario"] and row["strategy"] == case["strategy"]
               and row["model_label"] == case.get("model_label", "")
               and row["random_seed"] == str(case.get("random_seed", ""))]
    if len(matches) != 1:
        raise ValueError(f"{case['key']}: se esperaba una fila y hay {len(matches)}")
    return matches[0]


def _case_markdown(case, row, story) -> list[str]:
    name = STRATEGY_NAMES.get(row["strategy"], row["strategy"])
    if row["model_label"]:
        name += f" ({row['model_label']}, semilla de entrenamiento {row['training_seed'] or '—'})"
    lines = [f"## {case['role']}", ""]
    if case.get("note"):
        lines += [case["note"], ""]
    lines += _table(["Dato", "Valor"], [
        ["Escenario", f"`{row['scenario_path']}`"],
        ["Partición", row["partition"] + (f" ({row['manifest_id']})" if row["manifest_id"] else "")],
        ["Estrategia", name],
        ["Resultado", f"{OUTCOMES.get(row['outcome'], row['outcome'])}, "
                      f"{row['rescued']}/{row['victims_total']} personas, {row['steps']} de "
                      f"{row['max_steps']} pasos, daño {row['damage_total']}"],
        ["Episodio", f"`{row['episode_id']}` en `{case['results']}`"],
    ], numeric_from=2)
    lines += _table(["Robot", "Entregas", "Esperas", "Bloqueos", "Vaivenes", "Pasos con daño",
                     "Daño", "Integridad final", "Celdas distintas"],
                    [[str(i + 1), str(r["deliveries"]), str(r["waits"]), str(r["blocked"]),
                      str(r["back_and_forth"]), str(r["hot_steps"]), str(r["damage"]),
                      str(r["integrity"]), str(r["cells"])]
                     for i, r in enumerate(story["robots"])])
    if story["trips"]:
        lines += _table(["Persona", "Robot", "Recogida (paso)", "Entrega (paso)", "Duración"],
                        [[str(t["person"]), str(t["robot"]), str(t["pickup"]), str(t["delivery"]),
                          str(t["delivery"] - t["pickup"])] for t in story["trips"]])
    lines += ["Cronología observable:", ""]
    lines += [f"- {text}." for _, text in story["events"]]
    return lines + [""]


def build_trace_report(config_path: str | Path, root: str | Path) -> dict[str, bytes]:
    root = Path(root)
    config_path = Path(config_path)
    absolute = config_path if config_path.is_absolute() else root / config_path
    config = json.loads(absolute.read_text(encoding="utf-8"))
    rows_by_csv, traces_by_csv = {}, {}
    for csv_path in sorted({case["results"] for case in config["cases"]}):
        problems = verify_results(root / csv_path, root)
        if problems:
            raise ValueError(f"{csv_path} no está íntegro: " + "; ".join(problems[:3]))
        rows_by_csv[csv_path] = read_results(root / csv_path)
        traces = {}
        trace_path = (root / csv_path).with_suffix(".traces.jsonl")
        for line in trace_path.read_text(encoding="utf-8").splitlines():
            if line:
                record = json.loads(line)
                traces[record["episode_id"]] = record["actions"]
        traces_by_csv[csv_path] = traces
    lines = [
        "# Trazas analizadas (SARB-023)",
        "",
        "Archivo generado por `scripts/trace_story.py` desde "
        f"`{config_path.as_posix()}`. No se edita a mano. Cada episodio se reproduce en un motor "
        "nuevo y sus totales se comparan con la fila del CSV antes de describirlo.",
        "",
        "Definiciones: un **bloqueo** es un movimiento pedido que no cambió la posición de un "
        "robot operativo (pared, borde o el otro robot); un **vaivén** es volver a la celda "
        "ocupada dos pasos antes; las rachas se listan desde "
        f"{STREAK} pasos seguidos. Las celdas siguen la notación de la interfaz (A1 arriba a la "
        "izquierda).",
        "",
    ]
    for case in config["cases"]:
        row = _select(rows_by_csv[case["results"]], case)
        scenario = Scenario.load(root / row["scenario_path"])
        story = episode_story(scenario, traces_by_csv[case["results"]][row["episode_id"]])
        problems = _check_against_row(story, row)
        if problems:
            raise ValueError(f"{case['key']}: la traza no coincide con el CSV: {problems}")
        lines += _case_markdown(case, row, story)
    files = {"trazas.md": ("\n".join(lines).rstrip() + "\n").encode("utf-8")}
    sources = {
        "schema_version": ANALYSIS_SCHEMA, "generator": "sar_bot.trace_analysis",
        "config": {"path": config_path.as_posix(), "sha256": file_sha256(absolute)},
        "results": {path: file_sha256(root / path) for path in sorted(rows_by_csv)},
        "command": f"uv run python scripts/trace_story.py --cases {config_path.as_posix()} "
                   f"--output-dir {config.get('output_dir', 'results/sarb023')}",
        "outputs": {name: _content_sha256(data) for name, data in files.items()},
    }
    files["fuentes.json"] = (json.dumps(sources, indent=2, ensure_ascii=False) + "\n").encode()
    return files


def check_trace_report(output_dir: str | Path, root: str | Path) -> list[str]:
    root, output_dir = Path(root), Path(output_dir)
    try:
        sources = json.loads((output_dir / "fuentes.json").read_text(encoding="utf-8"))
        files = build_trace_report(sources["config"]["path"], root)
    except (OSError, ValueError, KeyError) as error:
        return [f"No se pudo regenerar: {error}"]
    problems = []
    for name, data in sorted(files.items()):
        path = output_dir / name
        if not path.is_file():
            problems.append(f"Falta {name}")
        elif _content_sha256(path.read_bytes()) != _content_sha256(data):
            problems.append(f"{name} no coincide con lo que producen las fuentes")
    return problems
