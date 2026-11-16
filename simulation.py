"""Headless evacuation simulation engine (no pygame needed)."""
import random

import numpy as np

from config import DT, SAMPLE_DT, DISCOVERY_RADIUS, EXIT_CLEARANCE, T_MAX
from geometry import build_walls
from metrics import Recorder, hand_calc_rset
from navigation import NavigationField
from scenarios import Scenario
from sfm_model import SFMParams, total_acceleration, local_density


class _Rng:
    """Small stand-in for numpy.random.Generator that only uses Python's standard library.

    (Avoids numpy.random, whose compiled module is blocked by some Windows security policies.)
    """

    def __init__(self, seed):
        self._r = random.Random(seed)

    def normal(self, mean, std, n):
        return np.array([self._r.gauss(mean, std) for _ in range(int(n))], dtype=float)

    def uniform(self, low, high, n=None):
        if n is None:
            return self._r.uniform(low, high)
        return np.array([self._r.uniform(low, high) for _ in range(int(n))], dtype=float)

    def random(self, n):
        return np.array([self._r.random() for _ in range(int(n))], dtype=float)


_AGENT_FIELDS = ("agent_id", "pos", "vel", "radius", "mass", "v0", "delay", "target", "discovered", "path0")


class Simulation:
    def __init__(self, scenario: Scenario, seed=0, params: SFMParams = SFMParams(), dt=DT):
        self.scenario = scenario
        self.params = params
        self.dt = dt
        self.room_w, self.room_h = scenario.room
        self.exits = scenario.exits
        self.pillar_list = [(p.x, p.y, p.radius) for p in scenario.pillars]
        self.nav = NavigationField(self.room_w, self.room_h, self.exits, scenario.pillars)
        self.reset(seed)

    # -- setup -----------------------------------------------------------------------
    def reset(self, seed=0):
        self.seed = seed
        self.rng = _Rng(seed)
        self.time = 0.0
        self.steps = 0
        self.evacuated = 0
        self.blocked = [e.is_blocked(0.0) for e in self.exits]
        self.walls = build_walls(self.room_w, self.room_h, self.exits, self.blocked)
        self.density_now = 0.0
        self._spawn()
        never_blocked = [e for e in self.exits if e.block_time is None]
        if len(never_blocked) == len(self.exits):
            ref = hand_calc_rset(self._unobstructed_arrivals(), sum(e.width for e in self.exits))
        else:
            ref = float("nan")
        self.recorder = Recorder(self.total, [e.width for e in self.exits],
                                 [e.name for e in self.exits], ref,
                                 flow_valid=not any((e.block_time or 0) > 0 for e in self.exits))

    def _spawn(self):
        sc, rng = self.scenario, self.rng
        n = sc.total_people
        radius = np.clip(rng.normal(0.25, 0.03, n), 0.20, 0.30)
        mass = np.clip(rng.normal(75.0, 12.0, n), 45.0, 110.0)
        v0 = np.clip(rng.normal(1.34, 0.26, n), 0.8, 1.9)
        slow = rng.random(n) < sc.slow_fraction
        v0[slow] = rng.uniform(0.5, 0.8, slow.sum())
        v0 = v0 * sc.speed_factor
        delay = rng.uniform(0.0, sc.reaction_max, n) if sc.reaction_max > 0 else np.zeros(n)

        placed, attempts = [], 0
        while len(placed) < n and attempts < n * 500:
            attempts += 1
            k = len(placed)
            p = np.array([rng.uniform(0.6, self.room_w - 0.6), rng.uniform(0.6, self.room_h - 0.6)])
            if any(np.hypot(p[0] - x, p[1] - y) < r + radius[k] + 0.3 for x, y, r in self.pillar_list):
                continue
            if all(np.hypot(*(p - q)) >= radius[k] + radius[m] + 0.15 for m, q in enumerate(placed)):
                placed.append(p)
        if len(placed) < n:
            print(f"Warning: could only place {len(placed)} of {n} people.")
        m = len(placed)
        self.total = m
        self.agent_id = np.arange(m)
        self.pos = np.array(placed, float).reshape(m, 2)
        self.vel = np.zeros((m, 2))
        self.radius, self.mass, self.v0, self.delay = radius[:m], mass[:m], v0[:m], delay[:m]
        self.discovered = np.zeros(m, bool)
        if sc.exit_choice == "nearest":
            d = np.stack([self.nav.distance(k, self.pos) for k in range(len(self.exits))])
            self.target = d.argmin(axis=0)
        else:
            self.target = np.full(m, sc.familiar_exit, dtype=int)
        self.path0 = np.array([self.nav.distance(int(t), self.pos[i:i + 1])[0]
                               for i, t in enumerate(self.target)])
        self._unobstructed = self.delay + self.path0 / np.maximum(self.v0, 1e-6)

    def _unobstructed_arrivals(self):
        return self._unobstructed

    # -- state -----------------------------------------------------------------------
    @property
    def remaining(self):
        return len(self.pos)

    @property
    def finished(self):
        return self.remaining == 0

    @property
    def timed_out(self):
        return self.time >= T_MAX and not self.finished

    # -- per-step logic --------------------------------------------------------------
    def _update_exit_states(self):
        new = [e.is_blocked(self.time) for e in self.exits]
        if new != self.blocked:
            self.blocked = new
            self.walls = build_walls(self.room_w, self.room_h, self.exits, self.blocked)

    def _update_targets(self):
        """Agents heading for a blocked door notice it near the door and re-route to the nearest open exit."""
        open_idx = [k for k, b in enumerate(self.blocked) if not b]
        if not open_idx:
            return
        for k, ex in enumerate(self.exits):
            if not self.blocked[k]:
                continue
            m = (self.target == k) & ~self.discovered
            if not m.any():
                continue
            near = np.hypot(*(self.pos - ex.mid(self.room_w, self.room_h)).T) <= DISCOVERY_RADIUS
            hit = m & near
            if hit.any():
                d = np.stack([self.nav.distance(o, self.pos[hit]) for o in open_idx])
                self.target[hit] = np.array(open_idx)[d.argmin(axis=0)]
                self.discovered[hit] = True

    def _desired_directions(self):
        dirs = np.zeros((self.remaining, 2))
        for k, ex in enumerate(self.exits):
            m = self.target == k
            if not m.any():
                continue
            p = self.pos[m]
            mid = ex.mid(self.room_w, self.room_h)
            half = max(0.0, ex.width / 2.0 - 0.35)
            t = np.clip((p - mid) @ ex.tangent, -half, half)
            aim = mid + t[:, None] * ex.tangent + ex.normal * 1.0
            straight = aim - p
            straight /= np.maximum(np.hypot(straight[:, 0], straight[:, 1]), 1e-9)[:, None]
            if self.pillar_list:
                field = self.nav.direction(k, p)
                use_field = ~self.nav.line_clear(p, aim) & (np.hypot(field[:, 0], field[:, 1]) > 0.5)
                straight = np.where(use_field[:, None], field, straight)
            dirs[m] = straight
        return dirs

    def _enforce_boundaries(self):
        """Hard safety net against tunnelling through walls (never triggers in normal operation)."""
        r, W, H = self.radius, self.room_w, self.room_h
        x, y = self.pos[:, 0], self.pos[:, 1]

        def in_open_gap(side, along):
            ok = np.zeros(len(along), bool)
            for e, b in zip(self.exits, self.blocked):
                if e.side == side and not b:
                    ok |= (along >= e.lo) & (along <= e.hi)
            return ok

        v = self.vel
        bad = (x < r) & ~in_open_gap("left", y)
        x[bad] = r[bad]; v[bad, 0] = np.maximum(v[bad, 0], 0)
        bad = (x > W - r) & ~in_open_gap("right", y)
        x[bad] = (W - r)[bad]; v[bad, 0] = np.minimum(v[bad, 0], 0)
        bad = (y < r) & ~in_open_gap("top", x)
        y[bad] = r[bad]; v[bad, 1] = np.maximum(v[bad, 1], 0)
        bad = (y > H - r) & ~in_open_gap("bottom", x)
        y[bad] = (H - r)[bad]; v[bad, 1] = np.minimum(v[bad, 1], 0)

    def _remove_evacuated(self):
        done = np.zeros(self.remaining, bool)
        via = np.full(self.remaining, -1)
        for k, ex in enumerate(self.exits):
            if self.blocked[k]:
                continue
            rel = self.pos - ex.mid(self.room_w, self.room_h)
            m = ((rel @ ex.normal) > EXIT_CLEARANCE) & (np.abs(rel @ ex.tangent) <= ex.width / 2) & ~done
            via[m] = k
            done |= m
        if not done.any():
            return
        for i in np.nonzero(done)[0]:
            self.recorder.log_exit(self.time, self.agent_id[i], via[i], self.delay[i], self.path0[i], self.v0[i])
        keep = ~done
        for name in _AGENT_FIELDS:
            setattr(self, name, getattr(self, name)[keep])
        self.evacuated += int(done.sum())

    def step(self):
        dt = self.dt
        self._update_exit_states()
        if self.remaining:
            self._update_targets()
            moving = self.delay <= self.time
            desired = (self.v0 * moving)[:, None] * self._desired_directions()
            acc = total_acceleration(self.pos, self.vel, self.radius, self.mass, desired,
                                     self.walls, self.pillar_list, self.params)
            self.vel += acc * dt
            speed = np.hypot(self.vel[:, 0], self.vel[:, 1])
            cap = np.maximum(self.params.max_speed_factor * self.v0, 0.5)
            self.vel *= np.where(speed > cap, cap / np.maximum(speed, 1e-12), 1.0)[:, None]
            self.pos += self.vel * dt
            self._enforce_boundaries()
            self._remove_evacuated()
        self.time += dt
        self.steps += 1
        if self.steps % int(round(SAMPLE_DT / dt)) == 0:
            self.density_now = local_density(self.pos) if self.remaining else 0.0
            sp = float(np.hypot(self.vel[:, 0], self.vel[:, 1]).mean()) if self.remaining else 0.0
            self.recorder.sample(self.time, self.evacuated, self.remaining, self.density_now, sp)

    def run(self, t_max=T_MAX):
        while not self.finished and self.time < t_max:
            self.step()
        return self.recorder.summary()