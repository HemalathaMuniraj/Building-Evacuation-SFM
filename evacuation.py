"""HTX building evacuation simulation - interactive viewer.

    python evacuation.py                       # open the viewer
    python evacuation.py --scenario "Two Exits" --seed 3
Keys: 1-7 scenario, R restart, SPACE pause, +/- speed, H heatmap, C colour mode, S screenshot, E export, ESC quit
"""
import argparse
import os
import sys

import numpy as np
import pygame

from config import DT, FPS, PX_PER_M, ROOM_ORIGIN_PX, T_MAX, WINDOW_SIZE
from dashboard import Dashboard
from scenarios import get_scenario, scenario_names
from simulation import Simulation

OX, OY = ROOM_ORIGIN_PX
BLACK, GREEN, RED, GREY = (30, 35, 40), (30, 170, 90), (210, 55, 55), (90, 100, 110)
BUILDING_FILL, MOVING, STOPPED, WAITING = (238, 243, 248), (35, 105, 210), (215, 60, 50), (150, 160, 172)
SPEEDS = [0.5, 1, 2, 4, 8, 16]
RESULTS_DIR = "results"


def px(x, y):
    return int(OX + x * PX_PER_M), int(OY + y * PX_PER_M)


def lerp(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def heat_color(d):
    t = max(0.0, min(1.0, d / 6.0))
    return (255, int(220 * (1 - t) + 40 * t), int(80 * (1 - t)), int(40 + 150 * t))


class Viewer:
    def __init__(self, scenario_name, seed):
        pygame.init()
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("HTX - Building Evacuation Simulation (Social Force Model)")
        self.clock = pygame.time.Clock()
        self.dash = Dashboard()
        self.f_label = pygame.font.SysFont("arial", 15, bold=True)
        self.f_title = pygame.font.SysFont("arial", 25, bold=True)
        self.f_note = pygame.font.SysFont("arial", 14)
        self.names = scenario_names()
        self.speed_idx, self.paused = 1, False
        self.show_heat, self.color_mode = False, "speed"
        self.message, self.saved = "", False
        self.load(scenario_name, seed)

    def load(self, name, seed):
        self.sim = Simulation(get_scenario(name), seed=seed)
        self.name, self.acc = name, 0.0
        self.message, self.saved, self.paused = "", False, False

    # -- input -----------------------------------------------------------------------
    def handle(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type != pygame.KEYDOWN:
            return True
        k = event.key
        if k == pygame.K_ESCAPE:
            return False
        if k == pygame.K_SPACE:
            self.paused = not self.paused
        elif k == pygame.K_r:
            self.load(self.name, self.sim.seed + 1)
        elif pygame.K_1 <= k < pygame.K_1 + len(self.names):
            self.load(self.names[k - pygame.K_1], 0)
        elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.speed_idx = min(self.speed_idx + 1, len(SPEEDS) - 1)
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.speed_idx = max(self.speed_idx - 1, 0)
        elif k == pygame.K_h:
            self.show_heat = not self.show_heat
        elif k == pygame.K_c:
            self.color_mode = "plain" if self.color_mode == "speed" else "speed"
        elif k == pygame.K_s:
            os.makedirs(RESULTS_DIR, exist_ok=True)
            path = os.path.join(RESULTS_DIR, f"screenshot_{self.name.replace(' ', '_')}_seed{self.sim.seed}.png")
            pygame.image.save(self.screen, path)
            self.message = f"Saved {path}"
        elif k == pygame.K_e:
            self.export()
        return True

    def export(self):
        prefix = f"gui_{self.name.replace(' ', '_')}_seed{self.sim.seed}"
        self.sim.recorder.save(RESULTS_DIR, prefix)
        self.message = f"Saved results/{prefix}_*.csv"

    # -- update ----------------------------------------------------------------------
    def update(self, real_dt):
        sim = self.sim
        if self.paused or sim.finished or sim.timed_out:
            if sim.finished and not self.saved:
                self.export()
                self.saved = True
            return
        self.acc += min(real_dt, 0.1) * SPEEDS[self.speed_idx]
        n = 0
        while self.acc >= DT and n < 600 and not sim.finished:
            sim.step()
            self.acc -= DT
            n += 1

    # -- drawing ---------------------------------------------------------------------
    def draw_room(self):
        sim, scr = self.sim, self.screen
        W, H = sim.room_w, sim.room_h
        pygame.draw.rect(scr, BUILDING_FILL, (OX, OY, int(W * PX_PER_M), int(H * PX_PER_M)))

        if self.show_heat and sim.remaining:
            cell = 0.5
            hist, _, _ = np.histogram2d(sim.pos[:, 0], sim.pos[:, 1], bins=[int(W / cell) + 1, int(H / cell) + 1],
                                        range=[[0, W + cell], [0, H + cell]])
            layer = pygame.Surface(scr.get_size(), pygame.SRCALPHA)
            for i, j in zip(*np.nonzero(hist)):
                pygame.draw.rect(layer, heat_color(hist[i, j] / (cell * cell)),
                                 (*px(i * cell, j * cell), int(cell * PX_PER_M), int(cell * PX_PER_M)))
            scr.blit(layer, (0, 0))

        for (a, b) in sim.walls:
            pygame.draw.line(scr, BLACK, px(*a), px(*b), 5)

        for k, ex in enumerate(sim.exits):
            p1, p2 = ex.endpoints(W, H)
            blocked = sim.blocked[k]
            col = RED if blocked else GREEN
            pygame.draw.line(scr, col, px(*p1), px(*p2), 9)

        for x, y, r in sim.pillar_list:
            pygame.draw.circle(scr, (120, 128, 138), px(x, y), int(r * PX_PER_M))
            pygame.draw.circle(scr, BLACK, px(x, y), int(r * PX_PER_M), 2)

        moving = sim.delay <= sim.time
        speed = np.hypot(sim.vel[:, 0], sim.vel[:, 1])
        for i in range(sim.remaining):
            if self.color_mode == "plain":
                col = MOVING
            elif not moving[i]:
                col = WAITING
            else:
                col = lerp(STOPPED, MOVING, min(1.0, speed[i] / max(sim.v0[i] * 0.8, 1e-6)))
            c = px(*sim.pos[i])
            rad = max(3, int(sim.radius[i] * PX_PER_M))
            pygame.draw.circle(self.screen, col, c, rad)
            pygame.draw.circle(self.screen, (15, 55, 120), c, rad, 1)

        for k, ex in enumerate(sim.exits):
            blocked = sim.blocked[k]
            col = RED if blocked else GREEN
            cx, cy = px(*(ex.mid(W, H) - ex.normal * 0.65))
            surf = self.f_label.render(ex.name.upper() + ("  BLOCKED" if blocked else ""), True, col)
            box = surf.get_rect(center=(cx, cy)).inflate(10, 4)
            box.clamp_ip(pygame.Rect(OX, OY, int(W * PX_PER_M), int(H * PX_PER_M)))
            pygame.draw.rect(self.screen, (255, 255, 255), box, border_radius=6)
            pygame.draw.rect(self.screen, col, box, 1, border_radius=6)
            self.screen.blit(surf, surf.get_rect(center=box.center))

    def draw(self):
        sim = self.sim
        self.screen.fill((250, 251, 253))
        self.screen.blit(self.f_title.render("BUILDING EVACUATION SIMULATION", True, BLACK), (100, 35))
        self.draw_room()

        rec = sim.recorder
        s = rec.summary()
        curve = rec.samples
        status = "PAUSED" if self.paused else "COMPLETE" if sim.finished else \
            "STALLED" if sim.timed_out else "RUNNING"
        self.dash.draw(self.screen, {
            "scenario": self.name, "description": sim.scenario.description,
            "total": sim.total, "evacuated": sim.evacuated, "remaining": sim.remaining,
            "elapsed": sim.time, "speed": SPEEDS[self.speed_idx], "seed": sim.seed,
            "curve_t": [c[0] for c in curve], "curve_e": [c[1] for c in curve],
            "t50": s["t50_s"], "t90": s["t90_s"], "peak_density": rec.peak_density,
            "flow": s["flow_p_s"], "status": status, "message": self.message,
        })

        notes = ["Agents: blue = walking freely, red = blocked / queuing, grey = not yet reacting",
                 "Green door = open, red door = blocked   |   Scale: 1 m = 50 px   |   Room "
                 f"{sim.room_w:.0f} m x {sim.room_h:.0f} m",
                 f"Social Force Model with contact forces   |   dt = {DT * 1000:.0f} ms"]
        for i, line in enumerate(notes):
            self.screen.blit(self.f_note.render(line, True, GREY), (100, 565 + 20 * i))
        pygame.display.flip()

    def run(self, max_frames=None, screenshot=None):
        frames, running = 0, True
        while running:
            real_dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                running = self.handle(event) and running
            self.update(real_dt)
            self.draw()
            frames += 1
            if max_frames and frames >= max_frames:
                if screenshot:
                    pygame.image.save(self.screen, screenshot)
                break
        pygame.quit()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", default=scenario_names()[0], choices=scenario_names())
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--frames", type=int, default=None, help="(testing) stop after N frames")
    ap.add_argument("--screenshot", default=None, help="(testing) save final frame to this PNG")
    args = ap.parse_args()
    Viewer(args.scenario, args.seed).run(args.frames, args.screenshot)
    sys.exit()


if __name__ == "__main__":
    main()