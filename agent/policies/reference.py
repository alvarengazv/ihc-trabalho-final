"""Analyst-only expert sequence. This module is never used as remote context."""

from agent.config import calibration_only
from agent.mechanisms.channel import criterion_span, criterion_visible, intersection


class Reference:
    def __init__(self, task, version):
        calibration_only(task)
        if task == "C1":
            self.steps = ([("touch", "category:2")] if version == "B" else []) + [
                ("read", "price:12"), ("read", "price:14"), ("read", "price:16"),
                ("touch", "open:14"), ("touch", "option:Individual"), ("touch", "add"),
                ("touch", "review"), ("read", "line:0"), ("read", "line-qty:0"),
                ("touch", "confirm")]
        else:
            review = [("read", f"{sign}:{i}") for i in range(4) for sign in ("line", "line-qty")]
            self.steps = [("touch", "review"), *review, ("touch", "inc:3"), ("touch", "confirm")]
        self.index = 0

    def choose(self, frame):
        while self.index < len(self.steps):
            kind, target = self.steps[self.index]
            match = next((e for e in frame.elements if (e["id"] if kind == "read" else e.get("action")) == target), None)
            if match is None:
                raise ValueError(f"Reference sign absent in scene {frame.scene}: {target}")
            visible = frame.visible.get(match["id"])
            clip = intersection(match.get("visible_box", match["box"]), frame.region)
            if visible and (kind != "read" or criterion_visible(match, clip)):
                self.index += 1
                if kind == "read":
                    continue
                return visible[1]["gesto"], ("touch", target)
            aim = next((span for line in match.get("text_lines", [])
                        if (span := criterion_span(match, line))), None) if kind == "read" else None
            x, y, width, height = aim or match.get("text_box", match["box"])
            vw, vh = frame.region[2:]
            # Expert navigates one aperture width/height per motor operation.
            tx = max(0, min(360 - vw, x + min(width, vw) / 2 - vw / 2))
            ty = max(0, min(max(0, frame.height - vh), y + min(height, vh) / 2 - vh / 2))
            dx, dy = tx - frame.x, ty - frame.y
            scale = max(1, abs(dx) / vw, abs(dy) / vh)
            destination = (frame.x + dx / scale, frame.y + dy / scale)
            if destination == (frame.x, frame.y):
                raise ValueError(f"Reference cannot reach {target}")
            return "DESLOCAR(ponto)", ("pan", destination)
        raise ValueError("Reference method exhausted before confirmation")

