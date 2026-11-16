"""Grid-based navigation: one Dijkstra distance field per exit.

Agents use a straight line to the door when nothing is in the way (natural-looking paths) and the
distance-field gradient when a pillar blocks the line of sight (obstacle avoidance).
"""
import heapq
import math
import numpy as np

_NEIGHBOURS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


class NavigationField:
    def __init__(self, room_w, room_h, exits, pillars, cell=0.25, margin=0.35):
        self.w, self.h, self.cell = room_w, room_h, cell
        self.nx, self.ny = int(math.ceil(room_w / cell)), int(math.ceil(room_h / cell))
        self.exits = exits
        self.pillars = pillars
        cx = (np.arange(self.nx) + 0.5) * cell
        cy = (np.arange(self.ny) + 0.5) * cell
        gx, gy = np.meshgrid(cx, cy, indexing="ij")
        free = np.ones((self.nx, self.ny), bool)
        for p in pillars:
            free &= np.hypot(gx - p.x, gy - p.y) > p.radius + margin
        self.free = free
        self.dist = np.full((len(exits), self.nx, self.ny), np.inf)
        self.dir = np.zeros((len(exits), self.nx, self.ny, 2))
        for k, ex in enumerate(exits):
            self._build(k, ex, gx, gy)

    # -- construction --------------------------------------------------------------
    def _seed_cells(self, ex, gx, gy):
        band = self.cell
        mid = ex.mid(self.w, self.h)
        rel_n = (gx - mid[0]) * ex.normal[0] + (gy - mid[1]) * ex.normal[1]
        rel_t = (gx - mid[0]) * ex.tangent[0] + (gy - mid[1]) * ex.tangent[1]
        return (rel_n > -band) & (rel_n <= 0) & (np.abs(rel_t) <= ex.width / 2.0) & self.free

    def _build(self, k, ex, gx, gy):
        D = self.dist[k]
        heap = []
        seeds = self._seed_cells(ex, gx, gy)
        for i, j in zip(*np.nonzero(seeds)):
            D[i, j] = 0.0
            heap.append((0.0, int(i), int(j)))
        heapq.heapify(heap)
        while heap:
            d, i, j = heapq.heappop(heap)
            if d > D[i, j]:
                continue
            for di, dj in _NEIGHBOURS:
                a, b = i + di, j + dj
                if 0 <= a < self.nx and 0 <= b < self.ny and self.free[a, b]:
                    nd = d + self.cell * (1.41421356 if di and dj else 1.0)
                    if nd < D[a, b]:
                        D[a, b] = nd
                        heapq.heappush(heap, (nd, a, b))
        dirs = self.dir[k]
        for i in range(self.nx):
            for j in range(self.ny):
                if not np.isfinite(D[i, j]):
                    continue
                if seeds[i, j]:
                    dirs[i, j] = ex.normal
                    continue
                v = np.zeros(2)
                for di, dj in _NEIGHBOURS:
                    a, b = i + di, j + dj
                    if 0 <= a < self.nx and 0 <= b < self.ny and D[a, b] < D[i, j]:
                        step = math.hypot(di, dj)
                        v += (D[i, j] - D[a, b]) / step * np.array([di, dj]) / step
                n = np.hypot(*v)
                if n > 1e-9:
                    dirs[i, j] = v / n

    # -- queries -------------------------------------------------------------------
    def _cell_index(self, pos):
        i = np.clip((pos[:, 0] / self.cell).astype(int), 0, self.nx - 1)
        j = np.clip((pos[:, 1] / self.cell).astype(int), 0, self.ny - 1)
        return i, j

    def distance(self, exit_idx, pos):
        """Walking distance to an exit [m]; large if unreachable."""
        i, j = self._cell_index(pos)
        d = self.dist[exit_idx][i, j]
        return np.where(np.isfinite(d), d, 1e3)

    def direction(self, exit_idx, pos):
        """Bilinearly interpolated unit direction toward the exit (zero vector where unknown)."""
        fx = np.clip(pos[:, 0] / self.cell - 0.5, 0, self.nx - 1.001)
        fy = np.clip(pos[:, 1] / self.cell - 0.5, 0, self.ny - 1.001)
        i0, j0 = fx.astype(int), fy.astype(int)
        tx, ty = (fx - i0)[:, None], (fy - j0)[:, None]
        D = self.dir[exit_idx]
        v = (D[i0, j0] * (1 - tx) * (1 - ty) + D[i0 + 1, j0] * tx * (1 - ty)
             + D[i0, j0 + 1] * (1 - tx) * ty + D[i0 + 1, j0 + 1] * tx * ty)
        n = np.hypot(v[:, 0], v[:, 1])
        return np.where(n[:, None] > 1e-9, v / np.maximum(n, 1e-9)[:, None], 0.0)

    def line_clear(self, start, end, margin=0.3):
        """True where the segment start->end does not pass through a pillar."""
        clear = np.ones(len(start), bool)
        seg = end - start
        denom = np.maximum((seg * seg).sum(1), 1e-12)
        for p in self.pillars:
            c = np.array([p.x, p.y])
            t = np.clip(((c - start) * seg).sum(1) / denom, 0, 1)
            closest = start + t[:, None] * seg
            clear &= np.hypot(*(closest - c).T) > p.radius + margin
        return clear