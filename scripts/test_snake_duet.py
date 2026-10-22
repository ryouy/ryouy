"""Behavior checks for the isolated randomized restoration animation."""
import re
import unittest
import xml.etree.ElementTree as ET

from generate_snake_duet import TAG, build_duet, plan_blue


def fixture():
    css = ':root{--cb:#0000000a;--cs:purple;--ce:#ebedf0;--c0:#ebedf0;--c1:#9be9a8;--c2:#40c463}'
    css += '.c{fill:var(--ce)}.s{fill:var(--cs);animation:none linear 1000ms infinite}'
    css += '@keyframes c0{10%{fill:var(--c1)}11%,100%{fill:var(--ce)}}'
    css += '@keyframes c1{60%{fill:var(--c2)}61%,100%{fill:var(--ce)}}'
    for i in range(4):
        css += f'@keyframes s{i}' + '{0%,100%{transform:translate(0px,-16px)}50%{transform:translate(16px,0px)}}'
        css += f'.s.s{i}' + '{transform:translate(0px,-16px);animation-name:s' + str(i) + '}'
    cells = '<rect class="c c0" x="2" y="2"/><rect class="c" x="2" y="18"/><rect class="c" x="18" y="2"/><rect class="c c1" x="18" y="18"/>'
    snake = ''.join(f'<rect class="s s{i}" x="1" y="1" width="12" height="12" rx="3"/>' for i in range(4))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-16 -32 64 100" width="64" height="100"><style>{css}</style>{cells}<rect class="u u0" y="60" width="32" height="12"/>{snake}</svg>'


class SnakeDuetTests(unittest.TestCase):
    def test_routes_cover_all_targets_without_teleports_or_body_collisions(self):
        targets = {(x, y) for x in range(0, 53, 3) for y in (0, 2, 4, 6)}
        signatures = set()
        for seed in range(12):
            states, visits = plan_blue(targets, 53, 7, 4, seed)
            self.assertEqual(set(visits), targets)
            signatures.add(tuple(state[0] for state in states))
            for before, after in zip(states, states[1:]):
                self.assertEqual(len(set(after)), 4)
                self.assertEqual(after[1:], before[:-1])
                self.assertEqual(sum(abs(a-b) for a, b in zip(before[0], after[0])), 1)
            for cell, visit in visits.items():
                self.assertEqual(states[visit][0], cell)
                self.assertIn(cell, states[visit + 3])
                self.assertTrue(any(cell not in state for state in states[visit + 4:]))
        self.assertEqual(len(signatures), 12)

    def test_routes_reproduce_with_same_seed(self):
        args = ({(1, 1), (3, 4), (10, 2)}, 12, 7, 4, 42)
        self.assertEqual(plan_blue(*args), plan_blue(*args))

    def test_svg_preserves_original_velocity_and_removes_all_gauges(self):
        source = fixture()
        root = ET.fromstring(build_duet(source, seed=42))
        self.assertEqual(float(root.get('data-original-red-ms')), 1000)
        self.assertEqual(float(root.get('data-step-ms')), 250)
        self.assertFalse(any('u' in el.get('class', '').split() for el in root.iter()))
        self.assertEqual(len(root.findall(TAG + 'g')), 2)
        for color in ('red', 'blue'):
            group = root.find(TAG + f"g[@class='duet-{color}']")
            self.assertEqual(len(group.findall(TAG + 'g')), 2)
            self.assertEqual(len(group.findall('.//' + TAG + 'rect')), 8)
        css = root.find(TAG + 'style').text
        self.assertNotIn('animation-direction:reverse', css)
        self.assertNotIn('@keyframes u0', css)
        self.assertIn('100%{fill:var(--c1)}', css)
        self.assertIn('100%{fill:var(--c2)}', css)
        self.assertLess(float(root.get('height')), 100)

    def test_restore_events_happen_after_tail_clears_each_cell(self):
        root = ET.fromstring(build_duet(fixture(), seed=42))
        css = root.find(TAG + 'style').text
        total = float(root.get('data-cycle-ms'))
        start = float(root.get('data-blue-start-ms'))
        step = float(root.get('data-step-ms'))
        for cell, name in [((0, 0), 'c0'), ((1, 1), 'c1')]:
            territory = cell[0]
            local = (0, cell[1])
            states, visits = plan_blue({local}, 1, 2, 4, 42 + 1009 + territory * 97,
                                      'left' if territory == 0 else 'right')
            body = re.search(r'@keyframes d-' + name + r'\{(.*?)\}\n', css).group(1)
            restore_pct = float(re.search(r'([\d.]+)%,100%\{fill:var\(--c[12]\)', body).group(1))
            tick = round((restore_pct * total / 100 - start) / step)
            self.assertGreaterEqual(tick, visits[local] + 4)
            self.assertNotIn(local, states[tick])

    def test_two_snakes_cannot_collide_or_process_the_same_targets(self):
        split, columns = 26, 53
        targets = {(x, y) for x in range(0, columns, 3) for y in (0, 2, 4, 6)}
        for seed in range(8):
            paths, assigned = [], []
            for index, (offset, width, side) in enumerate(((0, split, 'left'), (split, columns-split, 'right'))):
                local_targets = {(x-offset, y) for x, y in targets if offset <= x < offset+width}
                states, visits = plan_blue(local_targets, width, 7, 4, seed + index*97, side)
                paths.append([tuple((x+offset, y) for x, y in state) for state in states])
                assigned.append({(x+offset, y) for x, y in visits})
            self.assertEqual(assigned[0] | assigned[1], targets)
            self.assertFalse(assigned[0] & assigned[1])
            for tick in range(max(map(len, paths))):
                left = paths[0][min(tick, len(paths[0])-1)]
                right = paths[1][min(tick, len(paths[1])-1)]
                self.assertFalse(set(left) & set(right))
                self.assertTrue(all(x < split for x, y in left))
                self.assertTrue(all(x >= split for x, y in right))

    def test_invalid_inputs_fail_explicitly(self):
        with self.assertRaises(ValueError):
            build_duet('<svg xmlns="http://www.w3.org/2000/svg"/>')
        for speed in (-1, 0, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                build_duet(fixture(), step_ms=speed, seed=42)


if __name__ == '__main__':
    unittest.main()
