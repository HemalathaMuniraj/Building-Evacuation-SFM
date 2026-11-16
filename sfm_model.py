"""Social Force Model (Helbing, Farkas & Vicsek, Nature 2000) in SI units, vectorised with NumPy.

For agent i the acceleration is

    m_i dv_i/dt = m_i (v0_i e_i - v_i) / tau                      driving force
                + sum_j [ A exp((r_ij - d_ij)/B) + k g(r_ij-d_ij) ] n_ij
                        + kappa g(r_ij-d_ij) (dv_ji . t_ij) t_ij  other pedestrians
                + same terms for every wall segment and obstacle  boundaries

with g(x) = max(x, 0), n_ij the unit vector from j to i, and t_ij the tangent.
The first term in the bracket is the *psychological* repulsion, k g is the *body* compression
force and kappa g (...) is the *sliding friction*.  Contact forces are what produce realistic
clogging and arching in front of a door.
"""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class SFMParams:
    tau: float = 0.5               # relaxation time [s]
    a_ped: float = 2000.0          # pedestrian repulsion strength [N]
    b_ped: float = 0.08            # pedestrian repulsion range [m]
    a_wall: float = 2000.0         # wall repulsion strength [N]
    b_wall: float = 0.08           # wall repulsion range [m]
    k_body: float = 1.2e5          # body compression stiffness [kg/s^2]
    kappa: float = 2.4e5           # sliding friction coefficient [kg/(m s)]
    max_accel: float = 40.0        # numerical safety clamp [m/s^2]
    max_speed_factor: float = 1.3  # speed cap relative to the desired speed
    cutoff: float = 1.0            # ignore interactions beyond this gap [m]


def closest_point_on_segment(points, a, b):
    """Closest point on segment a-b for every row of `points` (N, 2)."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ab = b - a
    denom = float(ab @ ab)
    if denom < 1e-12:
        return np.broadcast_to(a, points.shape).copy()
    t = np.clip(((points - a) @ ab) / denom, 0.0, 1.0)
    return a + t[:, None] * ab


def driving_force(vel, mass, desired_vel, tau):
    return mass[:, None] * (desired_vel - vel) / tau


def pedestrian_forces(pos, vel, radius, p: SFMParams):
    """Pairwise agent-agent forces.  Only pairs closer than `cutoff` are evaluated."""
    n = len(pos)
    f = np.zeros((n, 2))
    if n < 2:
        return f
    dx = pos[:, None, 0] - pos[None, :, 0]
    dy = pos[:, None, 1] - pos[None, :, 1]
    d2 = dx * dx + dy * dy
    rsum = radius[:, None] + radius[None, :]
    near = np.triu(d2 < (rsum + p.cutoff) ** 2, 1)
    i, j = np.nonzero(near)
    if i.size == 0:
        return f
    d = np.maximum(np.sqrt(d2[i, j]), 1e-9)
    nx, ny = dx[i, j] / d, dy[i, j] / d
    overlap = rsum[i, j] - d
    g = np.maximum(overlap, 0.0)
    normal = p.a_ped * np.exp(np.clip(overlap / p.b_ped, -50.0, 50.0)) + p.k_body * g
    tx, ty = -ny, nx
    dvt = (vel[j, 0] - vel[i, 0]) * tx + (vel[j, 1] - vel[i, 1]) * ty
    fx = normal * nx + p.kappa * g * dvt * tx
    fy = normal * ny + p.kappa * g * dvt * ty
    # action = -reaction: what i feels, j feels with opposite sign
    f[:, 0] = np.bincount(i, fx, n) - np.bincount(j, fx, n)
    f[:, 1] = np.bincount(i, fy, n) - np.bincount(j, fy, n)
    return f


def _boundary_force(pos, vel, radius, closest, extra_radius, a, b, p):
    diff = pos - closest
    d = np.maximum(np.hypot(diff[:, 0], diff[:, 1]), 1e-9)
    nx, ny = diff[:, 0] / d, diff[:, 1] / d
    overlap = radius + extra_radius - d
    g = np.maximum(overlap, 0.0)
    normal = a * np.exp(np.clip(overlap / b, -50.0, 50.0)) + p.k_body * g
    tx, ty = -ny, nx
    vt = vel[:, 0] * tx + vel[:, 1] * ty
    fx = normal * nx - p.kappa * g * vt * tx
    fy = normal * ny - p.kappa * g * vt * ty
    return np.stack([fx, fy], axis=1)


def wall_forces(pos, vel, radius, walls, p: SFMParams):
    """Forces from wall segments (M, 2, 2)."""
    f = np.zeros((len(pos), 2))
    for a, b in walls:
        q = closest_point_on_segment(pos, a, b)
        f += _boundary_force(pos, vel, radius, q, 0.0, p.a_wall, p.b_wall, p)
    return f


def pillar_forces(pos, vel, radius, pillars, p: SFMParams):
    """Forces from circular obstacles given as [(x, y, R), ...]."""
    f = np.zeros((len(pos), 2))
    for x, y, r in pillars:
        c = np.broadcast_to(np.array([x, y]), pos.shape)
        f += _boundary_force(pos, vel, radius, c, r, p.a_wall, p.b_wall, p)
    return f


def total_acceleration(pos, vel, radius, mass, desired_vel, walls, pillars, p: SFMParams):
    force = driving_force(vel, mass, desired_vel, p.tau)
    force += pedestrian_forces(pos, vel, radius, p)
    force += wall_forces(pos, vel, radius, walls, p)
    if pillars:
        force += pillar_forces(pos, vel, radius, pillars, p)
    acc = force / mass[:, None]
    mag = np.hypot(acc[:, 0], acc[:, 1])
    scale = np.where(mag > p.max_accel, p.max_accel / np.maximum(mag, 1e-12), 1.0)
    return acc * scale[:, None]


def local_density(pos, radius=1.0):
    """Peak local density [persons / m^2], measured in a circle of the given radius around each agent."""
    n = len(pos)
    if n == 0:
        return 0.0
    dx = pos[:, None, 0] - pos[None, :, 0]
    dy = pos[:, None, 1] - pos[None, :, 1]
    counts = ((dx * dx + dy * dy) <= radius * radius).sum(axis=1)
    return float(counts.max() / (np.pi * radius * radius))