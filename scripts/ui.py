"""Abre SAR-Bot; permite generar capturas sin abrir ventanas con --headless."""

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, default=ROOT / "scenarios/pasillo_compartido.json")
    parser.add_argument("--strategy", choices=("dqn", "shortest", "thermal", "random"), default="dqn")
    parser.add_argument("--model", type=Path, default=ROOT / "artifacts/sensors_dqn/model.zip")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--steps", type=int, default=0, help="Pasos de la captura en modo headless")
    parser.add_argument("--screenshot", type=Path, default=ROOT / "outputs/ui-preview.png")
    args = parser.parse_args()
    if args.steps < 0:
        parser.error("--steps debe ser no negativo")
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    import pygame
    from sar_bot.ui.app import RescueApp, run_app
    # No inicializar audio: esta interfaz no lo necesita.
    pygame.display.init()
    pygame.font.init()
    app = RescueApp(ROOT, args.scenario, args.strategy, args.model, args.seed,
                    asynchronous=not args.headless)
    if args.headless:
        try:
            for _ in range(args.steps):
                app.playback.step()
            surface = app.render()
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(surface, str(args.screenshot))
            print(json.dumps({"steps": app.state.steps, "outcome": app.state.outcome,
                              "rescued": len(app.state.rescued), "screenshot": str(args.screenshot)}))
        finally:
            app.close()
            pygame.quit()
    else:
        run_app(app)


if __name__ == "__main__":
    main()
