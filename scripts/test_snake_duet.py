"""Behavior checks for the isolated randomized restoration animation."""
import re
import math
import unittest
import xml.etree.ElementTree as ET

from generate_snake_duet import TAG, build_duet, plan_pair, restart_pixels, restart_pixel_timing, assemble_message, morph_message, assembly_timeline, particle_contacts, grid_merge


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
    def test_restart_message_uses_grid_cells_only_between_snake_phases(self):
        pixels = restart_pixels(53, 7)
        self.assertGreater(len(pixels), 90)
        self.assertTrue(all(0 <= x < 53 and 0 <= y < 7 for x, y in pixels))
        self.assertFalse(restart_pixels(2, 2))
        source = ET.fromstring(fixture())
        for cell in list(source):
            if 'c' in cell.get('class', '').split():
                source.remove(cell)
        for x in range(53):
            for y in range(7):
                cls = 'c c0' if (x, y) == (1, 1) else 'c'
                ET.SubElement(source, TAG+'rect', {'class': cls, 'x': str(2+16*x), 'y': str(2+16*y)})
        root = ET.fromstring(build_duet(ET.tostring(source, encoding='unicode'), seed=42))
        message = root.find(TAG+"g[@class='restart-message']")
        self.assertIsNotNone(message)
        self.assertGreaterEqual(float(root.get('data-red-second-entry-delay-ms')), 900)
        actual = {(int(c.get('data-grid-x')), int(c.get('data-grid-y'))) for c in message}
        self.assertEqual(actual, pixels)
        self.assertEqual({c.get('fill') for c in message}, {'#4593f8', '#69a5ed'})
        self.assertTrue(all(c.get('transform') for c in message))
        self.assertEqual(root.get('data-message-model'), 'orthogonal-grid-collisions')
        self.assertEqual(len({(c.get('data-blue-snake'),c.get('data-morph-slot')) for c in message}),8)
        css = root.find(TAG+'style').text
        self.assertRegex(css, r'\.restart-cell-0\{animation:restart-cell-0 [\d.]+ms steps\(1,end\) infinite')
        self.assertIn('width:12.000px;height:12.000px;rx:2.000px',css)
        self.assertLess(float(root.get('data-red-ms')), float(root.get('data-message-start-ms')))
        self.assertEqual(float(root.get('data-message-end-ms')), float(root.get('data-blue-start-ms')))
        self.assertIn('.restart-message{animation:none;opacity:0}', root.find(TAG+'style').text)

    def test_particles_collide_then_assemble_exact_letters_without_overlaps(self):
        targets = restart_pixels(53, 7)
        for seed in (42, 123, 7919):
            paths, collisions = assemble_message(targets, 53, 7, seed)
            self.assertGreater(collisions, 0)
            self.assertEqual(len(paths), len(targets))
            self.assertEqual({p[-1] for p in paths}, targets)
            self.assertTrue(all(x < 0 or x >= 53 or y < 0 or y >= 7 for x,y in (p[0] for p in paths)))
            for tick in range(len(paths[0])):
                self.assertEqual(len({p[tick] for p in paths}), len(paths))
            for p in paths:
                self.assertTrue(all(abs(a[0]-b[0])+abs(a[1]-b[1]) in (0,1) for a,b in zip(p,p[1:])))
            self.assertEqual((paths, collisions), assemble_message(targets, 53, 7, seed))

    def test_settling_spans_four_seconds_and_contacts_stop_after_arrival(self):
        paths,_ = assemble_message(restart_pixels(53,7),53,7,42)
        times,stops = assembly_timeline(paths)
        self.assertAlmostEqual(max(times[t] for t in stops)-min(times[t] for t in stops),1200)
        self.assertGreater(len(set(stops)),3)
        self.assertGreater(len(set(stops)), 3)
        starts = [p[0] for p in paths]
        self.assertGreaterEqual(sum(x < 0 for x,y in starts), 1)
        self.assertGreaterEqual(sum(x >= 53 for x,y in starts), 1)
        self.assertGreaterEqual(sum(y < 0 for x,y in starts), 1)
        self.assertGreaterEqual(sum(y >= 7 for x,y in starts), 1)

    def test_message_merges_into_exact_blue_bodies(self):
        bodies = [tuple((17-i, 3) for i in range(4)), tuple((35+i, 3) for i in range(4))]
        paths = [[p] for p in sorted(restart_pixels(53, 7))]
        morphs = morph_message(paths, bodies)
        self.assertEqual({target for _,target,_ in morphs}, set(bodies[0]) | set(bodies[1]))
        for owner, target, route in morphs:
            self.assertIn(target, bodies[owner])
            self.assertEqual(route[-1], target)
            self.assertTrue(all(abs(a[0]-b[0])+abs(a[1]-b[1]) == 1 for a,b in zip(route,route[1:])))
        plans = plan_pair({(1,1),(50,5)},53,7,4,42,start_bodies=bodies)
        self.assertEqual([p['states'][0] for p in plans], bodies)

    def test_grid_merge_collisions_and_merge_only_at_shared_body_slots(self):
        paths,_=assemble_message(restart_pixels(53,7),53,7,42)
        bodies=[tuple((17-i,3) for i in range(4)),tuple((35+i,3) for i in range(4))]
        morphs=morph_message(paths,bodies)
        merged,collisions=grid_merge(paths,morphs,53,7,43)
        self.assertGreater(collisions,0)
        for i,path in enumerate(merged):
            self.assertEqual(path[-1],morphs[i][1])
            self.assertTrue(all(abs(a[0]-b[0])+abs(a[1]-b[1]) in (0,1) for a,b in zip(path,path[1:])))
        for tick in range(len(merged[0])):
            owners={}
            for i,path in enumerate(merged):
                point=path[tick]
                if point in owners:
                    j=owners[point]
                    self.assertEqual(point,morphs[i][1]);self.assertEqual(point,morphs[j][1])
                    self.assertEqual(morphs[i][0],morphs[j][0])
                owners[point]=i

    def test_red_snakes_wait_four_seconds_and_enter_separately(self):
        root = ET.fromstring(build_duet(fixture(), seed=42))
        self.assertEqual(float(root.get('data-intro-ms')), 4000)
        plans = plan_pair({(3, 2), (9, 4)},14,7,4,42,entry_delays=(0,10))
        self.assertTrue(all(b == plans[1]['states'][0] for b in plans[1]['states'][:11]))
        self.assertNotEqual(plans[0]['states'][0], plans[0]['states'][1])
        for a,b in zip(plans[0]['states'],plans[1]['states']):
            self.assertFalse(set(a) & set(b))

    def test_snakes_wander_after_completion_then_fully_leave(self):
        plans = plan_pair({(3, 2), (9, 4)}, 14, 7, 4, 42)
        complete = max(t for p in plans for t in p['visits'].values())
        for p in plans:
            after = p['states'][complete+1:complete+18]
            self.assertGreaterEqual(len(after), 16)
            self.assertGreater(sum(0 <= b[0][0] < 14 and 0 <= b[0][1] < 7 for b in after), 10)
            moves = [(b[0][0]-a[0][0], b[0][1]-a[0][1]) for a,b in zip(after,after[1:])]
            self.assertGreater(len(set(moves)-{(0,0)}), 1)
            self.assertTrue(all(x < 0 or x >= 14 or y < 0 or y >= 7 for x,y in p['states'][-1]))

    def test_shared_pool_coverage_and_collision_free_joint_routes(self):
        targets = {(x, y) for x in range(0, 53, 3) for y in (0, 2, 4, 6)}
        signatures = set()
        for seed in range(8):
            plans = plan_pair(targets, 53, 7, 4, seed)
            assigned = [set(plan['visits']) for plan in plans]
            self.assertEqual(assigned[0] | assigned[1], targets)
            self.assertFalse(assigned[0] & assigned[1])
            self.assertEqual(len(plans[0]['states']), len(plans[1]['states']))
            signatures.add(tuple(state[0] for state in plans[0]['states']))
            for plan in plans:
                for before, after in zip(plan['states'], plan['states'][1:]):
                    self.assertEqual(len(set(after)), 4)
                    distance = sum(abs(a-b) for a,b in zip(before[0],after[0]))
                    self.assertIn(distance, (0,1))
                    self.assertEqual(after, before if distance == 0 else (after[0],)+before[:-1])
                for cell, tick in plan['visits'].items():
                    self.assertEqual(plan['states'][tick][0], cell)
                    self.assertTrue(any(all(cell not in p['states'][t] for p in plans)
                                        for t in range(tick+4,len(plan['states']))))
            for left, right in zip(plans[0]['states'],plans[1]['states']):
                self.assertFalse(set(left)&set(right))
        self.assertEqual(len(signatures),8)

    def test_routes_reproduce_with_same_seed(self):
        args=({(1,1),(3,4),(10,2)},12,7,4,42)
        self.assertEqual(plan_pair(*args),plan_pair(*args))

    def test_real_grid_routes_can_cross_the_previous_midline(self):
        targets={(x,y) for x in range(8,53,3) for y in (0,2,4,6)}
        plans=plan_pair(targets,53,7,4,6869388369875623957)
        for plan in plans:
            xs=[state[0][0] for state in plan['states'] if 0<=state[0][0]<53]
            self.assertLess(min(xs),26)
            self.assertGreater(max(xs),26)

    def test_svg_keeps_velocity_has_four_tints_and_no_gauge(self):
        root=ET.fromstring(build_duet(fixture(),seed=42))
        self.assertEqual(float(root.get('data-original-red-ms')),1000)
        self.assertEqual(float(root.get('data-step-ms')),250)
        self.assertFalse(any('u' in el.get('class','').split() for el in root.iter()))
        css=root.find(TAG+'style').text
        tints=[]
        for color in ('red','blue'):
            group=root.find(TAG+f"g[@class='duet-{color}']")
            self.assertEqual(len(group.findall(TAG+'g')),2)
            self.assertEqual(len(group.findall('.//'+TAG+'rect')),8)
            for index in (0,1):
                match=re.search(r'\.snake-'+color+'-'+str(index)+r' \.s\{fill:(#[0-9a-f]+)',css)
                self.assertIsNotNone(match)
                tints.append(match.group(1))
        self.assertEqual(len(set(tints)),4)
        self.assertNotIn('animation-direction:reverse',css)
        self.assertIn('100%{fill:var(--c1)}',css)
        self.assertIn('100%{fill:var(--c2)}',css)

    def test_restore_events_wait_until_both_bodies_clear_the_cell(self):
        root=ET.fromstring(build_duet(fixture(),seed=42))
        plans=plan_pair({(0,0),(1,1)},2,2,4,42+1009)
        css=root.find(TAG+'style').text
        total=float(root.get('data-cycle-ms'))
        start=float(root.get('data-blue-start-ms'))
        step=float(root.get('data-step-ms'))
        for cell,name in [((0,0),'c0'),((1,1),'c1')]:
            owner=next(p for p in plans if cell in p['visits'])
            body=re.search(r'@keyframes d-'+name+r'\{(.*?)\}\n',css).group(1)
            restore_pct=float(re.search(r'([\d.]+)%,100%\{fill:var\(--c[12]\)',body).group(1))
            tick=round((restore_pct*total/100-start)/step)
            self.assertGreaterEqual(tick,owner['visits'][cell]+4)
            self.assertTrue(all(cell not in p['states'][tick] for p in plans))

    def test_invalid_inputs_fail_explicitly(self):
        with self.assertRaises(ValueError):
            build_duet('<svg xmlns="http://www.w3.org/2000/svg"/>')
        for speed in (-1,0,float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                build_duet(fixture(),step_ms=speed,seed=42)


if __name__=='__main__':
    unittest.main()
