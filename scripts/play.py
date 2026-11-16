"""Demostración visual: reproduce una estrategia sobre los escenarios de validación o prueba.

Controles: Espacio pausa · → un paso en pausa · R reinicia · N/B siguiente/anterior
           +/- velocidad · E cambia de estrategia · Esc sale

La velocidad solo cambia cuántos pasos se muestran por segundo: no altera el
tiempo simulado, las temperaturas ni el daño.

Ejemplos:
    python scripts/play.py
    python scripts/play.py --strategy dqn --model models/base_s0/best_model.zip
"""

from __future__ import annotations

import argparse
import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from sar_bot.agents import RandomPolicy, ShortestPathBaseline  # noqa: E402
from sar_bot.config import load_config  # noqa: E402
from sar_bot.env import RescueEnv  # noqa: E402
from sar_bot.ui.renderer import Renderer  # noqa: E402

AUTO_ADVANCE_S = 2.0
MIN_SPEED, MAX_SPEED = 0.5, 64.0


class Demo:
    def __init__(self, env: RescueEnv, policies: dict, strategy: str, speed: float, start: int) -> None:
        self.env = env
        self.scenarios = env.sampler.fixed
        self.policies = policies
        self.names = list(policies)
        self.current = self.names.index(strategy)
        self.speed = speed
        self.index = start % len(self.scenarios)
        self.paused = False
        self.load()

    @property
    def policy(self):
        return self.policies[self.names[self.current]]

    def load(self) -> None:
        self.observation, _ = self.env.reset(options={"scenario": self.scenarios[self.index]})
        self.policy.reset(self.env.sim)
        self.accumulator = 0.0
        self.end_timer = 0.0

    def advance(self) -> None:
        action = self.policy.act(self.observation, self.env.sim)
        self.observation, *_ = self.env.step(action)

    def handle_key(self, key: int) -> bool:
        """Procesa una tecla; devuelve False para salir."""
        if key == pygame.K_ESCAPE:
            return False
        if key == pygame.K_SPACE:
            self.paused = not self.paused
        elif key == pygame.K_RIGHT and self.paused and not self.env.sim.done:
            self.advance()
        elif key == pygame.K_r:
            self.load()
        elif key in (pygame.K_n, pygame.K_b):
            self.index = (self.index + (1 if key == pygame.K_n else -1)) % len(self.scenarios)
            self.load()
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.speed = min(self.speed * 2, MAX_SPEED)
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.speed = max(self.speed / 2, MIN_SPEED)
        elif key == pygame.K_e:
            self.current = (self.current + 1) % len(self.names)
            self.load()
        return True

    def update(self, dt: float) -> None:
        if self.paused:
            return
        if not self.env.sim.done:
            self.accumulator += dt
            interval = 1.0 / self.speed
            while self.accumulator >= interval and not self.env.sim.done:
                self.advance()
                self.accumulator -= interval
        else:
            self.end_timer += dt
            if self.end_timer >= AUTO_ADVANCE_S:
                self.index = (self.index + 1) % len(self.scenarios)
                self.load()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=None, help="archivo TOML (por defecto configs/base.toml)")
    parser.add_argument("--split", choices=("validation", "test"), default="validation")
    parser.add_argument("--strategy", choices=("referencia", "aleatoria", "dqn"), default="referencia")
    parser.add_argument("--model", default=None, help="modelo DQN .zip (habilita la estrategia dqn)")
    parser.add_argument("--speed", type=float, default=4.0, help="pasos mostrados por segundo")
    parser.add_argument("--start", type=int, default=0, help="índice del primer escenario")
    args = parser.parse_args()

    config = load_config(args.config)
    env = RescueEnv(config, split=args.split)
    policies = {"referencia": ShortestPathBaseline(), "aleatoria": RandomPolicy(seed=0)}
    if args.model:
        from sar_bot.agents.dqn import DQNPolicy

        policies["dqn"] = DQNPolicy.load(args.model)
    if args.strategy not in policies:
        raise SystemExit("la estrategia 'dqn' necesita --model")

    pygame.init()
    renderer = Renderer(env.sampler.shape, config.rules)
    screen = pygame.display.set_mode(renderer.size)
    pygame.display.set_caption("SAR-Bot")
    clock = pygame.time.Clock()
    demo = Demo(env, policies, args.strategy, args.speed, args.start)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                running = demo.handle_key(event.key)
        demo.update(dt)
        renderer.draw(
            screen,
            env.sim,
            strategy=demo.names[demo.current],
            paused=demo.paused,
            speed=demo.speed,
            episode=(demo.index + 1, len(demo.scenarios)),
        )
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
