# -*- coding: utf-8 -*-
"""Gera um Pong em SVG. Cada dia com commit vira um tijolo."""

import os
import re
import urllib.request
from pathlib import Path

USER = os.environ.get("GITHUB_USER", "Azulrok")
OUT = Path(os.environ.get("PONG_OUT", Path(__file__).resolve().parents[2] / "assets" / "pong.svg"))

CELL = 11
GAP = 3
STEP = CELL + GAP
LEFT = 20
TOP = 42
BALL_R = 5
PADDLE_W = 78
PADDLE_H = 8
DURATION = 22.0
FPS = 30

COLORS = {
    1: "#1F5560",
    2: "#2E8A96",
    3: "#3DCFC4",
    4: "#E4C27A",
}


def fetch_days(user):
    url = "https://github.com/users/{0}/contributions".format(user)
    req = urllib.request.Request(url, headers={"User-Agent": "Azulrok-pong"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    pattern = re.compile(
        r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*'
        r'id="contribution-day-component-(\d+)-(\d+)"[^>]*'
        r'data-level="(\d)"'
    )
    cells = []
    for date, row, col, level in pattern.findall(html):
        cells.append((int(col), int(row), date, int(level)))
    if not cells:
        raise SystemExit("calendario de contribuicoes vazio")
    return cells


def build_board(cells):
    weeks = max(item[0] for item in cells) + 1
    width = LEFT * 2 + weeks * STEP - GAP
    grid_bottom = TOP + 7 * STEP - GAP
    paddle_y = grid_bottom + 16
    height = paddle_y + PADDLE_H + 18
    bricks = []
    empties = []
    for week, day, date, level in cells:
        x = LEFT + week * STEP
        y = TOP + day * STEP
        if level <= 0:
            empties.append((x, y))
        else:
            bricks.append({
                "x": x,
                "y": y,
                "w": CELL,
                "h": CELL,
                "level": min(level, 4),
                "date": date,
                "alive": True,
                "hit": None,
            })
    return {
        "width": width,
        "height": height,
        "weeks": weeks,
        "left": LEFT,
        "right": LEFT + weeks * STEP - GAP,
        "top": TOP - 8,
        "paddle_y": paddle_y,
        "bricks": bricks,
        "empties": empties,
    }


def aim(ball_x, ball_y, bricks):
    best = None
    best_d = None
    for brick in bricks:
        if not brick["alive"]:
            continue
        cx = brick["x"] + brick["w"] / 2
        cy = brick["y"] + brick["h"] / 2
        dx = cx - ball_x
        dy = cy - ball_y
        dist = dx * dx + dy * dy
        if best_d is None or dist < best_d:
            best = cx
            best_d = dist
    return best


def simulate(board):
    bricks = board["bricks"]
    left = board["left"] + BALL_R
    right = board["right"] - BALL_R
    top = board["top"] + BALL_R
    paddle_y = board["paddle_y"]
    ball_x = (board["left"] + board["right"]) / 2
    ball_y = paddle_y - 24
    vx = 160.0
    vy = -220.0
    paddle_x = ball_x - PADDLE_W / 2
    frames = []
    steps = int(DURATION * FPS)
    dt = 1.0 / FPS
    substeps = 2
    sub_dt = dt / substeps

    for frame in range(steps):
        t = frame * dt
        for _ in range(substeps):
            target = ball_x - PADDLE_W / 2
            max_move = 220 * sub_dt
            if paddle_x < target:
                paddle_x = min(target, paddle_x + max_move)
            else:
                paddle_x = max(target, paddle_x - max_move)
            min_px = board["left"]
            max_px = board["right"] - PADDLE_W
            paddle_x = max(min_px, min(max_px, paddle_x))

            target_x = aim(ball_x, ball_y, bricks)
            if vy < 0 and target_x is not None:
                desired = max(-260.0, min(260.0, (target_x - ball_x) * 4))
                vx += (desired - vx) * 0.35
            elif target_x is None and abs(vx) < 90:
                vx = 160.0 if vx >= 0 else -160.0

            ball_x += vx * sub_dt
            ball_y += vy * sub_dt

            if ball_x < left:
                ball_x = left
                vx = abs(vx)
            elif ball_x > right:
                ball_x = right
                vx = -abs(vx)
            if ball_y < top:
                ball_y = top
                vy = abs(vy)

            if vy > 0 and paddle_y - BALL_R <= ball_y <= paddle_y + PADDLE_H:
                if paddle_x - BALL_R <= ball_x <= paddle_x + PADDLE_W + BALL_R:
                    ball_y = paddle_y - BALL_R
                    offset = (ball_x - (paddle_x + PADDLE_W / 2)) / (PADDLE_W / 2)
                    vx = offset * 240
                    vy = -max(170.0, abs(vy))

            hit = None
            hit_dist = None
            for brick in bricks:
                if not brick["alive"]:
                    continue
                cx = min(max(ball_x, brick["x"]), brick["x"] + brick["w"])
                cy = min(max(ball_y, brick["y"]), brick["y"] + brick["h"])
                dx = ball_x - cx
                dy = ball_y - cy
                dist = dx * dx + dy * dy
                if dist <= BALL_R * BALL_R and (hit_dist is None or dist < hit_dist):
                    hit = brick
                    hit_dist = dist
            if hit is not None:
                hit["alive"] = False
                hit["hit"] = t
                cx = min(max(ball_x, hit["x"]), hit["x"] + hit["w"])
                cy = min(max(ball_y, hit["y"]), hit["y"] + hit["h"])
                if abs(ball_x - cx) > abs(ball_y - cy):
                    vx = -vx
                else:
                    vy = -vy
                ball_x += vx * sub_dt
                ball_y += vy * sub_dt

            if ball_y > board["height"] + 20:
                ball_x = (board["left"] + board["right"]) / 2
                ball_y = paddle_y - 24
                vx = 150.0
                vy = -210.0

        frames.append((round(ball_x, 1), round(ball_y, 1), round(paddle_x, 1)))
    return frames


def opacity_anim(hit):
    t = max(0.02, min(hit / DURATION, 0.9))
    t2 = min(t + 0.02, 0.94)
    if t2 <= t:
        t2 = t + 0.01
    keys = "0;{0:.4f};{1:.4f};0.985;1".format(t, t2)
    return (
        '<animate attributeName="opacity" values="1;1;0;0;1" '
        'keyTimes="{0}" dur="{1}s" repeatCount="indefinite"/>'
    ).format(keys, int(DURATION) if DURATION == int(DURATION) else DURATION)


def render(board, frames):
    values_x = ";".join(str(item[0]) for item in frames)
    values_y = ";".join(str(item[1]) for item in frames)
    values_p = ";".join(str(item[2]) for item in frames)
    dur = "{0}s".format(int(DURATION) if DURATION == int(DURATION) else DURATION)
    parts = []
    add = parts.append
    add(
        '<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'.format(
            w=board["width"], h=board["height"]
        )
    )
    add("<title>Pong dos commits de Azulrok</title>")
    add('<rect width="100%" height="100%" rx="16" fill="#071E26"/>')
    add(
        '<rect x="1" y="1" width="{w}" height="{h}" rx="16" fill="none" stroke="#E4C27A"/>'.format(
            w=board["width"] - 2, h=board["height"] - 2
        )
    )
    add(
        '<text x="{x}" y="26" fill="#E4C27A" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="13" letter-spacing="2.4">PONG</text>'.format(
            x=LEFT
        )
    )
    add(
        '<text x="{x}" y="26" fill="#8FB4B8" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="12">commits viram tijolos</text>'.format(
            x=LEFT + 58
        )
    )
    for x, y in board["empties"]:
        add(
            '<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2" fill="#0C2C34"/>'.format(
                x=x, y=y, w=CELL, h=CELL
            )
        )
    for brick in board["bricks"]:
        anim = ""
        if brick["hit"] is not None:
            anim = opacity_anim(brick["hit"])
        add(
            '<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2" fill="{fill}">{anim}</rect>'.format(
                x=brick["x"],
                y=brick["y"],
                w=CELL,
                h=CELL,
                fill=COLORS[brick["level"]],
                anim=anim,
            )
        )
    add(
        '<rect y="{y}" width="{w}" height="{h}" rx="4" fill="#E4C27A">'
        '<animate attributeName="x" values="{values}" dur="{dur}" repeatCount="indefinite"/>'
        "</rect>".format(
            y=board["paddle_y"], w=PADDLE_W, h=PADDLE_H, values=values_p, dur=dur
        )
    )
    add(
        '<circle r="{r}" fill="#F6F3EA">'
        '<animate attributeName="cx" values="{vx}" dur="{dur}" repeatCount="indefinite"/>'
        '<animate attributeName="cy" values="{vy}" dur="{dur}" repeatCount="indefinite"/>'
        "</circle>".format(r=BALL_R, vx=values_x, vy=values_y, dur=dur)
    )
    add("</svg>\n")
    return "".join(parts)


def main():
    cells = fetch_days(USER)
    board = build_board(cells)
    frames = simulate(board)
    hits = sum(1 for brick in board["bricks"] if brick["hit"] is not None)
    svg = render(board, frames)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8", newline="\n")
    print("tijolos", len(board["bricks"]), "acertos", hits, "arquivo", OUT)


if __name__ == "__main__":
    main()
