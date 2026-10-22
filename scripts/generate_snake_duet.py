#!/usr/bin/env python3
"""Independent Snake experiment: two red snakes eat, two blue snakes restore.

Read-only inputs are Platane/snk's existing output-branch SVGs. Each color has
two snakes working in disjoint left/right regions. Routes choose nearby targets
randomly and use body-aware A*. Blue restores cells after its tail clears them.
All four snakes use the original animation's time per grid step. Only stdlib is
required. Outputs never include the original collection/progress bars.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import heapq
import itertools
import math
import random
import re
import statistics
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

NS = 'http://www.w3.org/2000/svg'
TAG = '{' + NS + '}'
ET.register_namespace('', NS)
ROOT = Path(__file__).resolve().parents[1]


def keyframes(css: str) -> dict:
    result = {}
    for name, body in re.findall(r'@keyframes (\w+)\{((?:[^{}]*\{[^{}]*\})+)\}', css):
        result[name] = {
            float(key.strip().rstrip('%')): declaration
            for keys, declaration in re.findall(r'([^{}]+)\{([^{}]+)\}', body)
            for key in keys.split(',')
        }
    return result


def point(declaration: str) -> tuple[float, float]:
    match = re.search(r'translate\((-?[\d.]+)px,\s*(-?[\d.]+)px\)', declaration)
    if not match:
        raise ValueError('Unrecognized source segment transform')
    return tuple(map(float, match.groups()))


def route_to(body, target, columns, rows, painted, rng, bounds=None):
    """Find adjacent moves without crossing the current four-segment body."""
    length = len(body)
    if bounds is None:
        bounds = (-length - 2, columns + length + 1, -length - 2, rows + length + 1)
    distance = lambda p: abs(p[0] - target[0]) + abs(p[1] - target[1])
    serial = itertools.count()
    queue = [(distance(body[0]), 0, next(serial), body)]
    costs, parents = {body: 0}, {}
    while queue:
        _, cost, _, state = heapq.heappop(queue)
        if cost != costs.get(state):
            continue
        if state[0] == target:
            path = []
            while state != body:
                path.append(state)
                state = parents[state]
            return list(reversed(path))
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        rng.shuffle(directions)
        for dx, dy in directions:
            head = (state[0][0] + dx, state[0][1] + dy)
            if not (bounds[0] <= head[0] <= bounds[1] and bounds[2] <= head[1] <= bounds[3]):
                continue
            # Moving into the old tail position is safe: it vacates this step.
            if head in state[:-1]:
                continue
            following = (head,) + state[:-1]
            following_cost = cost + 1 + (0.25 if head in painted else 0)
            if following_cost >= costs.get(following, math.inf):
                continue
            costs[following] = following_cost
            parents[following] = state
            heapq.heappush(queue, (following_cost + distance(head), following_cost,
                                   next(serial), following))
    raise ValueError(f'No body-safe path to {target}')


def plan_blue(targets, columns, rows, length, seed, side=None):
    """Return full body states plus the first head visit to every colored cell."""
    rng = random.Random(seed)
    row = rng.randrange(rows)
    from_left = side == 'left' if side else rng.choice((True, False))
    bounds = None
    if side:
        bounds = ((-length - 2, columns - 1, -length - 2, rows + length + 1)
                  if from_left else (0, columns + length + 1, -length - 2, rows + length + 1))
    body = tuple((-1 - i, row) if from_left else (columns + i, row) for i in range(length))
    states, visits = [body], {}
    pending = set(targets)

    def follow(path):
        for state in path:
            states.append(state)
            if state[0] in pending:
                visits[state[0]] = len(states) - 1
                pending.remove(state[0])

    while pending:
        head = states[-1][0]
        nearby = sorted(pending, key=lambda p: (abs(p[0] - head[0]) + abs(p[1] - head[1]), p))
        # Randomness has local intent, avoiding repeated full-width zigzags.
        target = rng.choice(nearby[:min(4, len(nearby))])
        follow(route_to(states[-1], target, columns, rows, set(visits), rng, bounds))
    exit_x = (-length - 1 if from_left else columns + length) if side else (columns + length if from_left else -length - 1)
    follow(route_to(states[-1], (exit_x, rng.randrange(rows)), columns, rows, set(visits), rng, bounds))
    if any(visit + length >= len(states) for visit in visits.values()):
        raise ValueError('Blue must leave enough steps for its tail to restore every cell')
    return states, visits


def compact_motion(points):
    """Keep turns and endpoints while dropping redundant constant-speed frames."""
    if len(points) < 3:
        return points
    kept = [points[0]]
    for previous, current, following in zip(points, points[1:], points[2:]):
        dt1, dt2 = current[0] - previous[0], following[0] - current[0]
        v1 = tuple((current[1][i] - previous[1][i]) / dt1 for i in (0, 1))
        v2 = tuple((following[1][i] - current[1][i]) / dt2 for i in (0, 1))
        if any(abs(a - b) > 1e-7 for a, b in zip(v1, v2)):
            kept.append(current)
    return kept + [points[-1]]


def build_duet(source: str, step_ms: float | None = None, seed: int | None = None) -> str:
    root = ET.fromstring(source)
    style = root.find(TAG + 'style')
    if style is None or not style.text:
        raise ValueError('Expected a Platane/snk SVG with animation CSS')
    css, frames = style.text, keyframes(style.text)
    duration_match = re.search(r'\.s\{[^}]*animation:[^;}]*?([\d.]+)ms', css)
    segments = sorted((el for el in root if 's' in el.get('class', '').split()),
                      key=lambda el: int(re.search(r'\bs(\d+)\b', el.get('class')).group(1)))
    cells = [el for el in root if 'c' in el.get('class', '').split()]
    if not duration_match or len(segments) < 2 or not cells or 's0' not in frames:
        raise ValueError('Unrecognized source animation structure')
    original_ms = float(duration_match.group(1))
    xs, ys = sorted({float(el.get('x')) for el in cells}), sorted({float(el.get('y')) for el in cells})
    pitch = min(b - a for a, b in zip(xs, xs[1:]))
    columns, rows = len(xs), len(ys)
    location = lambda el: (round((float(el.get('x')) - xs[0]) / pitch),
                           round((float(el.get('y')) - ys[0]) / pitch))
    colored = {location(el): el.get('class').split()[1] for el in cells if len(el.get('class').split()) == 2}
    red_points = sorted((time, point(decl)) for time, decl in frames['s0'].items())
    velocities = []
    for (t0, p0), (t1, p1) in zip(red_points, red_points[1:]):
        steps = (abs(p1[0] - p0[0]) + abs(p1[1] - p0[1])) / pitch
        if steps:
            velocities.append((t1 - t0) * original_ms / 100 / steps)
    original_step_ms = statistics.median(velocities)
    if step_ms is None:
        step_ms = original_step_ms
    if not math.isfinite(step_ms) or step_ms <= 0:
        raise ValueError('Step duration must be finite and positive')
    if seed is None:
        signature = repr(sorted(colored)) + date.today().isoformat()
        seed = int(hashlib.sha256(signature.encode()).hexdigest()[:16], 16)

    # Separate territories prevent both body/head collisions and duplicated work.
    split = columns // 2
    plans = {'red': [], 'blue': []}
    for phase, color in enumerate(('red', 'blue')):
        for index, (offset, width, side) in enumerate(((0, split, 'left'), (split, columns - split, 'right'))):
            targets = {(x - offset, y) for x, y in colored if offset <= x < offset + width}
            states, visits = plan_blue(targets, width, rows, len(segments), seed + phase * 1009 + index * 97, side)
            restoration = {
                coord: next(tick for tick in range(visit + len(segments), len(states))
                            if coord not in states[tick])
                for coord, visit in visits.items()
            }
            plans[color].append({'states': states, 'visits': visits, 'restore': restoration,
                                 'offset': offset, 'width': width})
    red_ms = max(len(p['states']) - 1 for p in plans['red']) * step_ms
    blue_start = red_ms + 700
    blue_end = blue_start + max(len(p['states']) - 1 for p in plans['blue']) * step_ms
    cycle_ms = blue_end + 1000
    pct = lambda time: f'{time / cycle_ms * 100:.7f}%'
    variables = re.search(r':root\{[^}]+\}', css).group(0)
    rules = [variables,
             f'.c{{shape-rendering:geometricPrecision;fill:var(--ce);stroke-width:1px;stroke:var(--cb);width:12px;height:12px;animation-duration:{cycle_ms:.3f}ms;animation-timing-function:linear;animation-iteration-count:infinite}}',
             f'.s{{shape-rendering:geometricPrecision;animation-duration:{cycle_ms:.3f}ms;animation-timing-function:linear;animation-iteration-count:infinite}}',
             '.duet-red .s{fill:#ef5350}', '.duet-blue .s{fill:#4593f8}',
             f'.duet-red{{animation:red-phase {cycle_ms:.3f}ms steps(1,end) infinite}}',
             f'.duet-blue{{opacity:0;animation:blue-phase {cycle_ms:.3f}ms steps(1,end) infinite}}',
             f'@keyframes red-phase{{0%{{opacity:1}}{pct(red_ms)},100%{{opacity:0}}}}',
             f'@keyframes blue-phase{{0%{{opacity:0}}{pct(blue_start)}{{opacity:1}}{pct(blue_end)},100%{{opacity:0}}}}']
    for coord, name in colored.items():
        level = re.search(r'var\(--(c\d+)\)', frames[name][min(frames[name])]).group(1)
        territory = 0 if coord[0] < split else 1
        red_plan, blue_plan = plans['red'][territory], plans['blue'][territory]
        local = (coord[0] - red_plan['offset'], coord[1])
        eat = red_plan['visits'][local] * step_ms
        restore = blue_start + blue_plan['restore'][local] * step_ms
        rules.append(f'@keyframes d-{name}{{0%,{pct(eat - 5)}{{fill:var(--{level})}}{pct(eat)},{pct(restore - 5)}{{fill:var(--ce)}}{pct(restore)},100%{{fill:var(--{level})}}}}')
        rules.append(f'.c.{name}{{fill:var(--{level});animation-name:d-{name}}}')
    for el in list(root):
        if el.tag == TAG + 'rect' and any(cls in el.get('class', '').split() for cls in ('s', 'u')):
            root.remove(el)
    for color in ('red', 'blue'):
        group = ET.SubElement(root, TAG + 'g', {'class': 'duet-' + color})
        for snake_index, plan in enumerate(plans[color]):
            snake = ET.SubElement(group, TAG + 'g', {'class': f'snake-{color}-{snake_index}'})
            start_ms = 0 if color == 'red' else blue_start
            for index, segment in enumerate(segments):
                rect = copy.deepcopy(segment)
                animation = f'{color}-{snake_index}-{index}'
                rect.set('class', 's ' + animation)
                motion = [(start_ms + tick * step_ms,
                           ((body[index][0] + plan['offset']) * pitch, body[index][1] * pitch))
                          for tick, body in enumerate(plan['states'])]
                motion = compact_motion(motion)
                if start_ms:
                    motion.insert(0, (0, motion[0][1]))
                initial = motion[0][1]
                rect.set('transform', f'translate({initial[0]:g} {initial[1]:g})')
                declarations = ''.join(f'{pct(time)}{{transform:translate({p[0]:g}px,{p[1]:g}px)}}' for time, p in motion)
                last = motion[-1][1]
                declarations += f'100%{{transform:translate({last[0]:g}px,{last[1]:g}px)}}'
                rules.append(f'@keyframes {animation}' + '{' + declarations + '}')
                rules.append(f'.s.{animation}{{animation-name:{animation}}}')
                snake.append(rect)
    rules.append('@media(prefers-reduced-motion:reduce){.c,.s{animation-duration:0s;animation-iteration-count:0}.duet-red,.duet-blue{animation:none;opacity:0}}')
    style.text = '\n'.join(rules)
    root.set('role', 'img')
    root.set('aria-label', 'Two red snakes eat contributions; two blue snakes restore them along independent randomized routes')
    for key, val in {'step-ms': step_ms, 'original-red-ms': original_ms, 'red-ms': red_ms,
                     'blue-start-ms': blue_start, 'blue-end-ms': blue_end, 'cycle-ms': cycle_ms}.items():
        root.set('data-' + key, f'{val:.3f}')
    root.set('data-seed', str(seed))
    root.set('data-snakes-per-color', '2')
    box = root.get('viewBox').split()
    box[3] = str(float(ys[-1]) + 28 - float(box[1]))
    root.set('viewBox', ' '.join(box));root.set('height', box[3])
    title = root.find(TAG + 'title')
    if title is None:
        title = ET.Element(TAG + 'title');root.insert(0, title)
    title.text = 'Contribution snakes — two eat, two restore'
    desc = root.find(TAG + 'desc')
    if desc is not None:
        desc.text = ('Independent experiment based on https://github.com/Platane/snk. '
                     'Two red snakes eat in parallel; two blue snakes restore original '
                     'colors behind their tails. Disjoint territories, independent '
                     'randomized body-safe paths, original movement speed, no gauge.')
    return ET.tostring(root, encoding='unicode') + '\n'

def load_source(local: Path | None, repository: str, dark: bool) -> str:
    if local:
        return local.read_text(encoding='utf-8')
    filename = 'github-contribution-grid-snake' + ('-dark' if dark else '') + '.svg'
    request = Request(f'https://raw.githubusercontent.com/{repository}/output/{filename}',
                      headers={'User-Agent': 'github-snake-duet/2.0'})
    with urlopen(request, timeout=30) as response:
        return response.read().decode('utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default='ryouy/ryouy')
    parser.add_argument('--source-light', type=Path)
    parser.add_argument('--source-dark', type=Path)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'assets')
    parser.add_argument('--step-ms', type=float, help='Defaults to the original Snake velocity')
    parser.add_argument('--seed', type=int, help='Optional reproducible route seed')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repository):
        parser.error('Expected owner/repository')
    inputs = {p.resolve() for p in (args.source_light, args.source_dark) if p}
    outputs = []
    for dark, local in ((False, args.source_light), (True, args.source_dark)):
        output = args.output_dir / ('snake-duet-dark.svg' if dark else 'snake-duet.svg')
        if output.resolve() in inputs:
            parser.error('Output must not overwrite a source SVG')
        outputs.append((output, build_duet(load_source(local, args.repository, dark), args.step_ms, args.seed)))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for output, svg in outputs:
        output.write_text(svg, encoding='utf-8')
        print(f'Generated {output.name}: original speed, randomized restoration, no gauge')


if __name__ == '__main__':
    main()
