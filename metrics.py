"""Recording, summarising and exporting evacuation metrics."""
import csv
import math
import os
import numpy as np

from config import REFERENCE_SPECIFIC_FLOW


class Recorder:
    def __init__(self, total, exit_widths, exit_names, rset_estimate=float("nan"), flow_valid=True):
        self.total = total
        self.exit_widths = list(exit_widths)
        self.exit_names = list(exit_names)
        self.rset_estimate = rset_estimate
        self.flow_valid = flow_valid      # False when exits change during the run (flow is then not meaningful)
        self.samples = []          # (t, evacuated, remaining, peak_density, mean_speed)
        self.events = []           # (agent_id, exit_idx, t_evac, delay, path0, v0)
        self.peak_density = 0.0

    # -- logging ---------------------------------------------------------------------
    def sample(self, t, evacuated, remaining, density, mean_speed):
        self.peak_density = max(self.peak_density, density)
        self.samples.append((t, evacuated, remaining, density, mean_speed))

    def log_exit(self, t, agent_id, exit_idx, delay, path0, v0):
        self.events.append((int(agent_id), int(exit_idx), float(t), float(delay), float(path0), float(v0)))

    # -- analysis --------------------------------------------------------------------
    @property
    def evac_times(self):
        return np.sort(np.array([e[2] for e in self.events], float))

    def fraction_evacuated(self, t_grid):
        times = self.evac_times
        return np.searchsorted(times, t_grid, side="right") / max(self.total, 1)

    def summary(self):
        times = self.evac_times
        n_ev = len(times)
        nan = float("nan")

        def t_at(frac):
            k = max(1, math.ceil(frac * self.total - 1e-9))
            return float(times[k - 1]) if n_ev >= k else nan

        per_exit = {name: 0 for name in self.exit_names}
        for _, k, *_ in self.events:
            per_exit[self.exit_names[k]] += 1
        active_width = sum(w for w, name in zip(self.exit_widths, self.exit_names)
                           if n_ev and per_exit[name] >= 0.05 * n_ev)

        flow = spec_flow = nan
        k1, k2 = max(1, int(0.2 * self.total)), max(2, int(0.8 * self.total))
        if self.flow_valid and n_ev >= k2 and k2 > k1 and times[k2 - 1] > times[k1 - 1] and active_width > 0:
            flow = (k2 - k1) / (times[k2 - 1] - times[k1 - 1])
            spec_flow = flow / active_width

        eff = [(p / v) / max(t - d, 1e-6) for _, _, t, d, p, v in self.events if v > 0]
        t100 = t_at(1.0)
        out = {
            "total_people": self.total,
            "evacuated": n_ev,
            "finished": n_ev == self.total,
            "t50_s": t_at(0.5),
            "t90_s": t_at(0.9),
            "t100_s": t100,
            "mean_egress_s": float(times.mean()) if n_ev else nan,
            "median_egress_s": float(np.median(times)) if n_ev else nan,
            "peak_density_p_m2": round(self.peak_density, 2),
            "flow_p_s": flow,
            "specific_flow_p_m_s": spec_flow,
            "reference_specific_flow": REFERENCE_SPECIFIC_FLOW,
            "mean_travel_efficiency": float(np.mean(eff)) if eff else nan,
            "rset_hand_calc_s": self.rset_estimate,
        }
        for name, c in per_exit.items():
            out[f"via_{name.replace(' ', '_')}"] = c
        return out

    # -- export ----------------------------------------------------------------------
    def save(self, directory, prefix):
        os.makedirs(directory, exist_ok=True)
        paths = {}
        paths["summary"] = os.path.join(directory, f"{prefix}_summary.csv")
        with open(paths["summary"], "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["metric", "value"])
            for k, v in self.summary().items():
                w.writerow([k, round(v, 3) if isinstance(v, float) else v])
        paths["agents"] = os.path.join(directory, f"{prefix}_agents.csv")
        with open(paths["agents"], "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["agent_id", "exit", "evacuation_time_s", "reaction_delay_s", "path_length_m", "desired_speed_m_s"])
            for a, k, t, d, p, v in sorted(self.events, key=lambda e: e[2]):
                w.writerow([a, self.exit_names[k], round(t, 2), round(d, 2), round(p, 2), round(v, 2)])
        paths["curve"] = os.path.join(directory, f"{prefix}_curve.csv")
        with open(paths["curve"], "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time_s", "evacuated", "remaining", "peak_density_p_m2", "mean_speed_m_s"])
            for row in self.samples:
                w.writerow([round(row[0], 2), row[1], row[2], round(row[3], 2), round(row[4], 3)])
        return paths


def hand_calc_rset(arrivals, total_exit_width, specific_flow=REFERENCE_SPECIFIC_FLOW):
    """Textbook egress estimate: max(first arrival + N / (Fs * W), last arrival).

    `arrivals` is every occupant's unobstructed (reaction delay + walking) time to the exit.
    """
    arrivals = np.asarray(arrivals, float)
    if arrivals.size == 0 or total_exit_width <= 0:
        return float("nan")
    return float(max(arrivals.min() + arrivals.size / (specific_flow * total_exit_width), arrivals.max()))