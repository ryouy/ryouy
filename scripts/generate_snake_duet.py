#!/usr/bin/env python3
"""Independent Snake experiment: two red snakes eat, two blue snakes restore.

Read-only inputs are Platane/snk's existing output-branch SVGs. Each color has
two snakes sharing the entire grid. Routes choose nearby targets
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


def route_to(body, target, columns, rows, painted, rng, bounds=None, blocked=None):
    """Find adjacent moves without crossing the current four-segment body."""
    length = len(body)
    blocked = blocked or set()
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
            if head in state[:-1] or head in blocked:
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


def plan_pair(targets, columns, rows, length, seed, start_bodies=None, entry_delays=None):
    """Two roaming snakes share one target pool, with collision-safe joint moves."""
    rng = random.Random(seed)
    entry_delays = entry_delays or (0, 0)
    bounds = (-length-4, columns+length+3, -length-4, rows+length+3)
    # A body must start as a straight, connected snake, not random individual cells.
    left_row, right_row = rng.randrange(rows), rng.randrange(rows)
    bodies = [tuple((-1-i, left_row) for i in range(length)),
              tuple((columns+i, right_row) for i in range(length))]
    if start_bodies is not None:
        bodies = list(start_bodies)
    histories = [[body] for body in bodies]
    pending, claims = set(targets), [{}, {}]
    goals, exits = [None, None], [None, None]
    stall = 0
    wander = [rng.randint(20, 32) for _ in (0, 1)]
    final_exit = [False, False]

    def exit_goal(head):
        x, y = min(max(head[0], 0), columns-1), min(max(head[1], 0), rows-1)
        choices = [(-length-2, y), (columns+length+1, y),
                   (x, -length-3), (x, rows+length+2)]
        return min(choices, key=lambda p: abs(p[0]-head[0])+abs(p[1]-head[1])+rng.random()*4)

    def options(index):
        body, other = bodies[index], bodies[1-index]
        if tick <= entry_delays[index]:
            return [(0, body)]
        target = goals[index] if pending else exits[index]
        if not pending and body[0] == target:
            return [(0, body)]
        try:
            preferred = route_to(body, target, columns, rows, set(targets)-pending,
                                 rng, bounds, set(other))
            preferred = preferred[0] if preferred else body
        except ValueError:
            preferred = None
        result = []
        for dx, dy in ((1,0), (-1,0), (0,1), (0,-1)):
            head = (body[0][0]+dx, body[0][1]+dy)
            if not(bounds[0]<=head[0]<=bounds[1] and bounds[2]<=head[1]<=bounds[3]):
                continue
            if head in body[:-1]:
                continue
            state = (head,)+body[:-1]
            distance = abs(head[0]-target[0])+abs(head[1]-target[1])
            score = distance + (0 if state == preferred else 4) + rng.random()*.25
            if head in pending:
                score -= 2
            result.append((score, state))
        # Waiting is a last resort, allowing the other snake to clear the way.
        result.append((abs(body[0][0]-target[0])+abs(body[0][1]-target[1])+20, body))
        return result

    for tick in range(1, columns*rows*40+200):
        if not pending and all(final_exit[i] and bodies[i][0] == exits[i] for i in (0,1)):
            break
        if pending:
            for index in rng.sample((0,1), 2):
                if goals[index] not in pending or goals[index] == goals[1-index] or stall>60:
                    available = pending - {goals[1-index]}
                    available = available or pending
                    head = bodies[index][0]
                    nearby = sorted(available, key=lambda p:(abs(p[0]-head[0])+abs(p[1]-head[1]),p))
                    # Usually stay purposeful; occasionally choose a broader detour.
                    choices = 14 if rng.random()<.12 else 5
                    goals[index] = rng.choice(nearby[:min(choices,len(nearby))])
        else:
            for index in (0,1):
                if wander[index] > 0:
                    head = bodies[index][0]
                    if exits[index] is None or head == exits[index] or wander[index] % 6 == 0:
                        exits[index] = (min(columns-1, max(0, head[0]+rng.randint(-5, 5))),
                                        min(rows-1, max(0, head[1]+rng.randint(-3, 3))))
                    wander[index] -= 1
                elif not final_exit[index]:
                    exits[index] = exit_goal(bodies[index][0])
                    final_exit[index] = True
        pairs = []
        candidates = [options(0), options(1)]
        for score0, state0 in candidates[0]:
            for score1, state1 in candidates[1]:
                if set(state0).isdisjoint(state1):
                    pairs.append((score0+score1, state0, state1))
        if not pairs:
            raise ValueError('No collision-safe joint step')
        _, first, second = min(pairs, key=lambda p:p[0])
        bodies = [first, second]
        removed = 0
        for index, body in enumerate(bodies):
            histories[index].append(body)
            if body[0] in pending:
                claims[index][body[0]] = tick
                pending.remove(body[0]);removed += 1
        stall = 0 if removed else stall+1
    else:
        raise ValueError('Shared-route planning exceeded its step budget')
    return [{'states':histories[i], 'visits':claims[i], 'offset':0, 'width':columns}
            for i in (0,1)]

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


def restart_pixels(columns, rows):
    """Center a five-row ONCE MORE message on actual contribution-grid cells."""
    glyphs = {
        'O': ('01110', '10001', '10001', '10001', '01110'),
        'N': ('10001', '11001', '10101', '10011', '10001'),
        'C': ('01111', '10000', '10000', '10000', '01111'),
        'E': ('11111', '10000', '11110', '10000', '11111'),
        'M': ('10001', '11011', '10101', '10001', '10001'),
        'R': ('11110', '10001', '11110', '10100', '10010'),
    }
    phrase = 'ONCE MORE'
    width = sum(3 if char == ' ' else 6 for char in phrase) - 1
    if columns < width or rows < 5:
        return set()
    x, y = (columns-width)//2, (rows-5)//2
    pixels = set()
    for char in phrase:
        if char == ' ':
            x += 3
            continue
        for row, bits in enumerate(glyphs[char]):
            pixels.update((x+col, y+row) for col, bit in enumerate(bits) if bit == '1')
        x += 6
    return pixels


def restart_pixel_timing(index, count, start):
    """Each cell switches independently, in a visible 24ms grid cadence."""
    return start + index*24, start + count*24 + 1600 + (count-1-index)*24


def assemble_message(targets, columns, rows, seed):
    """Forward four-sided particle simulation with elastic block contacts."""
    rng = random.Random(seed)
    goals = sorted(targets)
    rng.shuffle(goals)
    count = len(goals)
    deadlines = list(range(count))
    rng.shuffle(deadlines)
    deadlines = [5500 + i*4000/max(1,count-1) for i in deadlines]
    positions, velocities = [], []
    for i in range(count):
        side, lane = i%4, i//4
        if side == 0:
            p = [-1-lane//rows, (lane%rows)+rng.uniform(-.08,.08)]
        elif side == 1:
            p = [columns+lane//rows, (lane%rows)+rng.uniform(-.08,.08)]
        elif side == 2:
            p = [rng.uniform(0,columns-1), -1-rng.random()*2]
        else:
            p = [rng.uniform(0,columns-1), rows+rng.random()*2]
        positions.append(p)
        velocities.append([rng.uniform(-1,1),rng.uniform(-1,1)])
    histories = [[tuple(p)] for p in positions]
    collisions = 0
    dt = .04
    frozen = [False]*count
    for tick in range(1,239):
        now = tick*40
        for i,(p,v) in enumerate(zip(positions,velocities)):
            if now >= deadlines[i]:
                p[:] = goals[i];v[:] = [0,0];frozen[i]=True
                continue
            if now < 2200:
                # Opposing streams converge through a dense central collision zone.
                aim = (columns/2 + math.sin(i*2.4)*columns*.24,
                       rows/2 + math.cos(i*1.7)*1.5)
                force = 3.5
            else:
                aim = goals[i]
                force = 7 if deadlines[i]-now > 1000 else 22
            v[0] = (v[0]+(aim[0]-p[0])*force*dt)*.84
            v[1] = (v[1]+(aim[1]-p[1])*force*dt)*.84
            speed = math.hypot(*v)
            if speed > 11:
                v[0] *= 11/speed;v[1] *= 11/speed
            p[0] += v[0]*dt;p[1] += v[1]*dt
        # Repeated separation and normal impulses create actual visible impacts.
        for sweep in range(3):
            for i in range(count):
                for j in range(i):
                    dx,dy = positions[i][0]-positions[j][0],positions[i][1]-positions[j][1]
                    if abs(dx)>=.78 or abs(dy)>=.78 or (frozen[i] and frozen[j]):
                        continue
                    axis = 0 if abs(dx)>abs(dy) else 1
                    delta = dx if axis==0 else dy
                    sign = 1 if delta>=0 else -1
                    overlap = .78-abs(delta)
                    wi,wj = (0 if frozen[i] else 1),(0 if frozen[j] else 1)
                    total=wi+wj
                    positions[i][axis] += sign*overlap*wi/total
                    positions[j][axis] -= sign*overlap*wj/total
                    relative=(velocities[i][axis]-velocities[j][axis])*sign
                    if relative < 0:
                        impulse=-relative*1.8/total
                        velocities[i][axis]+=sign*impulse*wi
                        velocities[j][axis]-=sign*impulse*wj
                        if sweep==0:collisions+=1
        for i,p in enumerate(positions):
            remaining = deadlines[i]-now
            if 0 < remaining <= 1600:
                blend = min(1, 40/remaining)
                p[0] += (goals[i][0]-p[0])*blend
                p[1] += (goals[i][1]-p[1])*blend
            if frozen[i]:p[:]=goals[i]
            histories[i].append(tuple(p))
    # Exact final grid coordinates; subsequent timing maps first/last arrivals to 4s.
    for i,p in enumerate(goals):
        histories[i][-1]=p
    last_change = max(max(i for i in range(1,len(path)) if path[i] != path[i-1]) for path in histories)
    histories = [path[:last_change+1] for path in histories]
    return histories,collisions


def assembly_timeline(paths):
    """Spread the actual first-to-last final arrivals over exactly four seconds."""
    stops = [max(i for i in range(1, len(p)) if p[i] != p[i-1]) for p in paths]
    first, last = min(stops), max(stops)
    times = [tick*70 if tick <= first else first*70+(tick-first)*4000/max(1,last-first)
             for tick in range(len(paths[0]))]
    return times, stops


def particle_contacts(paths, stops):
    """Pair neighboring unsettled blocks for a small, visible contact/recoil."""
    bumps = [{} for _ in paths]
    for tick in range(len(paths[0])-1):
        occupied = {path[tick]: i for i,path in enumerate(paths)}
        used = set()
        for i, path in enumerate(paths):
            if i in used or tick >= stops[i]:
                continue
            x,y = path[tick]
            for dx,dy in ((1,0),(0,1),(-1,0),(0,-1)):
                j = occupied.get((x+dx,y+dy))
                if j is not None and j not in used and tick < stops[j]:
                    bumps[i][tick] = (dx*2,dy*2)
                    bumps[j][tick] = (-dx*2,-dy*2)
                    used.update((i,j))
                    break
    return bumps


def morph_message(paths, bodies):
    """Merge letter cells into the exact eight initial blue-snake segments."""
    counts = [0, 0]
    result = []
    for path in paths:
        x, y = path[-1]
        owner = min((0, 1), key=lambda i: abs(x-bodies[i][0][0])+abs(y-bodies[i][0][1]))
        target = bodies[owner][counts[owner] % len(bodies[owner])]
        counts[owner] += 1
        points = [(x, y)]
        # Straight grid lanes visibly gather the word into two small bodies.
        while y != target[1]:
            y += 1 if target[1] > y else -1
            points.append((x, y))
        while x != target[0]:
            x += 1 if target[0] > x else -1
            points.append((x, y))
        result.append((owner, target, points))
    return result


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

    message_pixels = restart_pixels(columns, rows)
    blue_bodies = [tuple((columns//3-i, rows//2) for i in range(len(segments))),
                   tuple((2*columns//3+i, rows//2) for i in range(len(segments)))] if message_pixels else None
    plans = {}
    for phase, color in enumerate(('red', 'blue')):
        plans[color] = plan_pair(colored, columns, rows, len(segments), seed + phase*1009 + (17041 if color == 'red' and columns >= 8 else 0),
                                 blue_bodies if color == 'blue' else None,
                                 (0, max(1, round(1000/step_ms))) if color == 'red' and columns >= 8 else None)
        for plan in plans[color]:
            plan['restore'] = {
                coord: next(tick for tick in range(visit+len(segments), len(plan['states']))
                            if all(coord not in snake['states'][tick] for snake in plans[color]))
                for coord, visit in plan['visits'].items()
            }
    intro_ms = 4000
    red_ms = intro_ms + max(len(p['states']) - 1 for p in plans['red']) * step_ms
    message_start = red_ms + 350
    particle_paths, collision_count = assemble_message(message_pixels, columns, rows, seed+7919) if message_pixels else ([], 0)
    assembly_times, settle_ticks = assembly_timeline(particle_paths) if particle_paths else ([], [])
    bumps = [{} for _ in particle_paths]
    assembly_ms = assembly_times[-1] if particle_paths else 0
    morphs = morph_message(particle_paths, blue_bodies) if message_pixels else []
    morph_start = message_start + assembly_ms + 1600
    morph_ms = 5600 if morphs else 0
    message_end = morph_start + morph_ms + 150
    blue_start = message_end if message_pixels else red_ms + 700
    blue_end = blue_start + max(len(p['states']) - 1 for p in plans['blue']) * step_ms
    cycle_ms = blue_end + 1000
    pct = lambda time: f'{time / cycle_ms * 100:.7f}%'
    variables = re.search(r':root\{[^}]+\}', css).group(0)
    rules = [variables,
             f'.c{{shape-rendering:geometricPrecision;fill:var(--ce);stroke-width:1px;stroke:var(--cb);width:12px;height:12px;animation-duration:{cycle_ms:.3f}ms;animation-timing-function:linear;animation-iteration-count:infinite}}',
             f'.s{{shape-rendering:geometricPrecision;animation-duration:{cycle_ms:.3f}ms;animation-timing-function:linear;animation-iteration-count:infinite}}',
             '.snake-red-0 .s{fill:#ef5350}', '.snake-red-1 .s{fill:#f06b68}',
             '.snake-blue-0 .s{fill:#4593f8}', '.snake-blue-1 .s{fill:#69a5ed}',
             f'.duet-red{{animation:red-phase {cycle_ms:.3f}ms steps(1,end) infinite}}',
             f'.duet-blue{{opacity:0;animation:blue-phase {cycle_ms:.3f}ms steps(1,end) infinite}}',
             f'@keyframes red-phase{{0%{{opacity:1}}{pct(red_ms)},100%{{opacity:0}}}}',
             f'@keyframes blue-phase{{0%{{opacity:0}}{pct(blue_start)}{{opacity:1}}{pct(blue_end)},100%{{opacity:0}}}}']
    for coord, name in colored.items():
        level = re.search(r'var\(--(c\d+)\)', frames[name][min(frames[name])]).group(1)
        red_plan = next(plan for plan in plans['red'] if coord in plan['visits'])
        blue_plan = next(plan for plan in plans['blue'] if coord in plan['visits'])
        eat = intro_ms + red_plan['visits'][coord] * step_ms
        restore = blue_start + blue_plan['restore'][coord] * step_ms
        rules.append(f'@keyframes d-{name}{{0%,{pct(eat - 5)}{{fill:var(--{level})}}{pct(eat)},{pct(restore - 5)}{{fill:var(--ce)}}{pct(restore)},100%{{fill:var(--{level})}}}}')
        rules.append(f'.c.{name}{{fill:var(--{level});animation-name:d-{name}}}')
    for el in list(root):
        if el.tag == TAG + 'rect' and any(cls in el.get('class', '').split() for cls in ('s', 'u')):
            root.remove(el)
    for color in ('red', 'blue'):
        group = ET.SubElement(root, TAG + 'g', {'class': 'duet-' + color})
        for snake_index, plan in enumerate(plans[color]):
            snake = ET.SubElement(group, TAG + 'g', {'class': f'snake-{color}-{snake_index}'})
            start_ms = intro_ms if color == 'red' else blue_start
            for index, segment in enumerate(segments):
                rect = copy.deepcopy(segment)
                animation = f'{color}-{snake_index}-{index}'
                rect.set('class', 's ' + animation)
                if color == 'blue':
                    shades = (('#4593f8','#3e87e6','#377bd4','#306fc2'),
                              ('#69a5ed','#609be0','#5791d3','#4e87c6'))
                    rules.append(f'.snake-blue-{snake_index} .{animation}'+f'{{fill:{shades[snake_index][index]}}}')
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
    if message_pixels:
        message = ET.SubElement(root, TAG+'g', {
            'class': 'restart-message', 'aria-label': 'ONCE MORE',
            'clip-path': 'url(#message-grid)',
        })
        defs = ET.SubElement(root, TAG+'defs')
        clip = ET.SubElement(defs, TAG+'clipPath', {'id': 'message-grid'})
        ET.SubElement(clip, TAG+'rect', {
            'x': f'{xs[0]-.5:g}', 'y': f'{ys[0]-.5:g}',
            'width': f'{xs[-1]-xs[0]+13:g}', 'height': f'{ys[-1]-ys[0]+13:g}',
        })
        cells_by_coord = {location(c): c for c in cells}
        for index, path in enumerate(particle_paths):
            coord = path[-1]
            pixel = copy.deepcopy(cells_by_coord[coord])
            pixel.set('class', f'restart-pixel restart-cell-{index}')
            pixel.set('width', '12'); pixel.set('height', '12')
            owner, target, gathering = morphs[index]
            pixel.set('fill', ('#4593f8', '#69a5ed')[owner])
            pixel.set('data-morph-x', str(target[0])); pixel.set('data-morph-y', str(target[1]))
            pixel.set('data-blue-snake', str(owner))
            pixel.set('data-grid-x', str(coord[0])); pixel.set('data-grid-y', str(coord[1]))
            animation = f'restart-cell-{index}'
            initial = ((path[0][0]-coord[0])*pitch, (path[0][1]-coord[1])*pitch)
            pixel.set('transform', f'translate({initial[0]:g} {initial[1]:g})')
            motion = [(0, initial)] + [(message_start+assembly_times[tick],
                       ((p[0]-coord[0])*pitch,(p[1]-coord[1])*pitch)) for tick,p in enumerate(path)]
            declarations = ''.join(f'{pct(t)}'+'{'+f'transform:translate({p[0]:.2f}px,{p[1]:.2f}px)'+'}'
                                   for t,p in motion)
            slot = list(blue_bodies[owner]).index(target)
            segment = segments[slot]
            final = ((target[0]-coord[0])*pitch+float(segment.get('x'))-xs[0],
                     (target[1]-coord[1])*pitch+float(segment.get('y'))-ys[0])
            shades = (('#4593f8','#3e87e6','#377bd4','#306fc2'),
                      ('#69a5ed','#609be0','#5791d3','#4e87c6'))
            base_color = ('#4593f8','#69a5ed')[owner]
            end_color = shades[owner][slot]
            rgb = lambda color: tuple(int(color[i:i+2],16) for i in (1,3,5))
            begin_rgb,end_rgb = rgb(base_color),rgb(end_color)
            begin = morph_start+(index%7)*50
            declarations += f'{pct(morph_start)}'+'{transform:translate(0px,0px);width:12px;height:12px;rx:2px;ry:2px;fill:'+base_color+'}'
            for frame in range(41):
                t = frame/40
                u = t*t*(3-2*t)
                # One continuous curved flow, without vertical/horizontal sections.
                arc = math.sin(math.pi*u)*(coord[1]-rows/2)*2.5
                px,py = final[0]*u,final[1]*u+arc
                width = 12+(float(segment.get('width'))-12)*u
                height = 12+(float(segment.get('height'))-12)*u
                radius = 2+(float(segment.get('rx','3'))-2)*u
                fill = '#'+''.join(f'{round(a+(b-a)*u):02x}' for a,b in zip(begin_rgb,end_rgb))
                declarations += f'{pct(begin+t*5200)}'+'{'+f'transform:translate({px:.3f}px,{py:.3f}px);width:{width:.3f}px;height:{height:.3f}px;rx:{radius:.3f}px;ry:{radius:.3f}px;fill:{fill};opacity:1'+'}'
            declarations += '100%{'+f'transform:translate({final[0]:.3f}px,{final[1]:.3f}px);width:{segment.get("width")}px;height:{segment.get("height")}px;rx:{segment.get("rx")}px;ry:{segment.get("ry")}px;fill:{end_color};opacity:1'+'}'
            pixel.set('data-morph-slot',str(slot))
            rules.append(f'@keyframes {animation}'+'{'+declarations+'}')
            rules.append(f'.{animation}'+f'{{animation:{animation} {cycle_ms:.3f}ms linear infinite}}')
            message.append(pixel)
        root.set('data-message-model', 'forward-elastic-four-sides')
        root.set('data-red-route-salt', '17041')
        root.set('data-message-collisions', str(collision_count))
        root.set('data-message-visible-contacts', str(collision_count))
        root.set('data-message-first-settled-ms', f'{message_start+min(assembly_times[t] for t in settle_ticks):.3f}')
        root.set('data-message-settle-span-ms', '4000')
        root.set('data-message-morph-duration-ms', f'{morph_ms:.3f}')
        root.set('data-message-morph-start-ms', f'{morph_start:.3f}')
        root.set('data-message-formed-ms', f'{message_start+assembly_ms:.3f}')
        rules.append(f'.restart-message{{opacity:0;animation:restart-message {cycle_ms:.3f}ms steps(1,end) infinite}}')
        rules.append(f'@keyframes restart-message{{0%,{pct(message_start)}{{opacity:0}}'
                     f'{pct(message_start+1)},{pct(message_end-1)}{{opacity:1}}'
                     f'{pct(message_end)},100%{{opacity:0}}}}')
        root.set('data-message-start-ms', f'{message_start:.3f}')
        root.set('data-message-end-ms', f'{message_end:.3f}')
    rules.append('@media(prefers-reduced-motion:reduce){.c,.s{animation-duration:0s;animation-iteration-count:0}.duet-red,.duet-blue,.restart-message{animation:none;opacity:0}}')
    style.text = '\n'.join(rules)
    root.set('role', 'img')
    root.set('aria-label', 'Two red snakes eat contributions; two blue snakes restore them along independent randomized routes')
    for key, val in {'step-ms': step_ms, 'original-red-ms': original_ms, 'red-ms': red_ms,
                     'blue-start-ms': blue_start, 'blue-end-ms': blue_end, 'cycle-ms': cycle_ms}.items():
        root.set('data-' + key, f'{val:.3f}')
    root.set('data-intro-ms', str(intro_ms))
    root.set('data-red-second-entry-delay-ms', str(max(1, round(1000/step_ms))*step_ms if columns >= 8 else 0))
    root.set('data-seed', str(seed))
    root.set('data-snakes-per-color', '2')
    box = root.get('viewBox').split()
    box[0] = f'{xs[0]-.5:g}'
    box[2] = f'{xs[-1]-xs[0]+13:g}'
    root.set('width', box[2])
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
                     'colors behind their tails. Shared grid, independent '
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
