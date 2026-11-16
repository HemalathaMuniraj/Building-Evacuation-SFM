"""pygame dashboard panel (fonts are cached, layout is data-driven)."""
import pygame

INK, MUTED, BLUE, GREEN, RED, AMBER = (35, 45, 55), (105, 115, 128), (35, 90, 150), (25, 135, 75), (190, 75, 55), (190, 120, 20)


class Dashboard:
    def __init__(self, rect=(830, 20, 300, 660)):
        self.rect = pygame.Rect(rect)
        self.f_title = pygame.font.SysFont("arial", 19, bold=True)
        self.f_head = pygame.font.SysFont("arial", 17, bold=True)
        self.f_body = pygame.font.SysFont("arial", 16)
        self.f_small = pygame.font.SysFont("arial", 13)

    def _text(self, screen, text, x, y, font=None, color=INK):
        screen.blit((font or self.f_body).render(str(text), True, color), (x, y))

    def _row(self, screen, label, value, y, color=INK):
        x = self.rect.x + 20
        self._text(screen, label, x, y, self.f_head)
        surf = self.f_head.render(str(value), True, color)
        screen.blit(surf, (self.rect.right - 20 - surf.get_width(), y))

    def _wrap(self, screen, text, x, y, width, font, color):
        line = ""
        for word in text.split():
            test = (line + " " + word).strip()
            if font.size(test)[0] > width and line:
                self._text(screen, line, x, y, font, color)
                y += font.get_height() + 1
                line = word
            else:
                line = test
        if line:
            self._text(screen, line, x, y, font, color)
        return y + font.get_height()

    def draw(self, screen, s):
        r, x = self.rect, self.rect.x + 20
        pygame.draw.rect(screen, (242, 245, 249), r, border_radius=14)
        pygame.draw.rect(screen, (190, 200, 212), r, 2, border_radius=14)
        self._text(screen, "EVACUATION DASHBOARD", x, r.y + 16, self.f_title)

        self._text(screen, s["scenario"], x, r.y + 52, self.f_head, BLUE)
        y = self._wrap(screen, s["description"], x, r.y + 76, r.width - 40, self.f_small, MUTED)

        y = max(y + 8, r.y + 130)
        self._row(screen, "Total people", s["total"], y)
        self._row(screen, "Evacuated", s["evacuated"], y + 26, GREEN)
        self._row(screen, "Remaining", s["remaining"], y + 52, RED)

        bar = pygame.Rect(x, y + 88, r.width - 40, 18)
        pygame.draw.rect(screen, (215, 222, 230), bar, border_radius=8)
        progress = s["evacuated"] / s["total"] if s["total"] else 0
        w = int(bar.width * max(0, min(1, progress)))
        if w:
            pygame.draw.rect(screen, (40, 165, 100), (bar.x, bar.y, w, bar.height), border_radius=8)
        self._text(screen, f"{progress * 100:.1f}%", x, y + 108, self.f_body)

        minutes, seconds = int(s["elapsed"] // 60), int(s["elapsed"] % 60)
        self._row(screen, "Sim time", f"{minutes:02d}:{seconds:02d}", y + 134)
        self._row(screen, "Speed / seed", f"{s['speed']}x / {s['seed']}", y + 160, MUTED)

        # evacuation curve
        cy = y + 196
        self._text(screen, "Evacuation curve", x, cy, self.f_head)
        chart = pygame.Rect(x, cy + 24, r.width - 40, 80)
        pygame.draw.rect(screen, (255, 255, 255), chart)
        pygame.draw.rect(screen, (200, 208, 218), chart, 1)
        ts, es = s["curve_t"], s["curve_e"]
        if len(ts) > 1 and s["total"]:
            t_max = max(30.0, ts[-1])
            pts = [(chart.x + t / t_max * chart.width,
                    chart.bottom - e / s["total"] * chart.height) for t, e in zip(ts, es)]
            pygame.draw.lines(screen, (40, 165, 100), False, pts, 2)
        self._text(screen, "time →", chart.right - 42, chart.bottom + 1, self.f_small, MUTED)

        # live metrics
        my = chart.bottom + 24
        def fmt(v, unit=""):
            return "–" if v != v else f"{v:.1f}{unit}"
        self._row(screen, "T50 / T90", f"{fmt(s['t50'])} / {fmt(s['t90'])} s", my)
        self._row(screen, "Peak density", f"{s['peak_density']:.1f} p/m²", my + 24,
                  RED if s["peak_density"] >= 4 else INK)
        self._row(screen, "Door flow", "–" if s["flow"] != s["flow"] else f"{s['flow']:.2f} p/s", my + 48)

        status, color = s["status"], {"RUNNING": MUTED, "PAUSED": AMBER, "COMPLETE": GREEN,
                                      "STALLED": RED}.get(s["status"], MUTED)
        self._text(screen, status, x, my + 80, self.f_head, color)
        if s.get("message"):
            self._text(screen, s["message"], x, my + 102, self.f_small, MUTED)

        ky = r.bottom - 82
        for i, line in enumerate(("1-7: scenario   R: restart (new seed)", "SPACE: pause   +/-: sim speed",
                                  "H: density heatmap   C: colour mode", "S: screenshot   E: export CSV   ESC: quit")):
            self._text(screen, line, x, ky + i * 18, self.f_small, MUTED)