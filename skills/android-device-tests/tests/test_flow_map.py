"""Tests of the flow map script, on made-up runs in throwaway folders."""
import html
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / 'scripts' / 'flow_map.py'


def walk(pictures, flow, steps, clips=(), told=None, at=None):
    """Leave a flow's pictures the way a test run does: numbered step pictures, and a clip for some."""
    folder = pictures / flow
    folder.mkdir(parents=True)
    for number, step in enumerate(steps, 1):
        picture = folder / f'{number:02d}-{step}.png'
        picture.write_bytes(f'{flow} {step}'.encode())
        if step in clips:
            picture.with_suffix('.gif').write_bytes(f'{flow} {step} moving'.encode())
        if at:
            for file in (picture, picture.with_suffix('.gif')):
                if file.exists():
                    os.utime(file, (at, at))
    (folder / 'flow.png').write_bytes(b'the sheet')
    if told:
        (folder / 'flow.json').write_text(json.dumps(told))


def draw(pictures, folder, *options, fails=False):
    done = subprocess.run([sys.executable, '-I', str(SCRIPT), str(pictures), str(folder), *options],
                          capture_output=True, text=True)
    if (done.returncode != 0) != fails:
        raise AssertionError(done.stdout + done.stderr)
    return done.stdout + done.stderr


class FlowMapTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.pictures = Path(temp.name).resolve() / 'pictures'
        self.map = Path(temp.name).resolve() / 'flow-map'
        self.pictures.mkdir()

    def page(self):
        return (self.map / 'index.html').read_text(encoding='utf-8')

    def flows(self):
        return json.loads((self.map / 'flows.json').read_text(encoding='utf-8'))['flows']

    def shown(self):
        return json.loads((self.map / 'pictures.json').read_text(encoding='utf-8'))


class JoiningFlows(FlowMapTest):
    def test_flows_share_the_screens_they_start_with_and_part_with_an_arrow_each(self):
        walk(self.pictures, 'test-sign-in', ['screen-a', 'screen-b', 'screen-c'])
        walk(self.pictures, 'test-sign-up', ['screen-a', 'screen-b', 'screen-d'])

        out = draw(self.pictures, self.map)

        page = self.page()
        self.assertIn('Flow map: 2 flows on 4 screens', out)
        self.assertEqual(page.count('<figure class="screen'), 4)
        self.assertEqual(page.count('data-name="Screen b"'), 1)
        self.assertEqual(page.count('<path data-flows='), 3)  # a to b once, then b to c and b to d
        self.assertIn('data-flows=" 0 1 " data-name="Screen b"', page)
        self.assertIn('data-flows=" 1 " data-name="Screen d"', page)

    def test_the_same_name_on_another_path_is_another_screen(self):
        walk(self.pictures, 'test-sign-in', ['welcome', 'lock', 'the-sheet-opens-again'])
        walk(self.pictures, 'test-sign-up', ['welcome', 'sheet', 'the-sheet-opens-again'])

        draw(self.pictures, self.map)

        self.assertEqual(self.page().count('data-name="The sheet opens again"'), 2)

    def test_a_flow_that_ends_where_another_goes_on_is_named_under_that_screen(self):
        walk(self.pictures, 'test-open', ['welcome'])
        walk(self.pictures, 'test-open-and-sign-in', ['welcome', 'home'])

        draw(self.pictures, self.map)

        welcome = self.page().split('data-name="Welcome"')[1].split('</figure>')[0]
        self.assertIn('>Open</li>', welcome)
        self.assertNotIn('Open and sign in', welcome)

    def test_a_shared_screen_shows_the_picture_of_the_flow_walked_last(self):
        walk(self.pictures, 'test-old', ['welcome', 'home'], at=1_000_000)
        walk(self.pictures, 'test-new', ['welcome', 'settings'], at=2_000_000)

        draw(self.pictures, self.map)

        welcome = self.page().split('data-name="Welcome"')[1].split('</figure>')[0]
        self.assertIn('<img src="screens/test-new/01-welcome.png"', welcome)

    def test_a_shared_screen_keeps_each_flows_own_picture_for_when_that_flow_is_picked(self):
        walk(self.pictures, 'test-sign-in', ['welcome', 'home'], clips=['welcome'], at=1_000_000)
        walk(self.pictures, 'test-sign-up', ['welcome', 'setup'], clips=['welcome'], at=2_000_000)

        draw(self.pictures, self.map)

        welcome, home = (self.page().split(f'data-name="{name}"')[1].split('</figure>')[0] for name in ('Welcome', 'Home'))
        own = json.loads(html.unescape(welcome.split('data-own="')[1].split('"')[0]))
        self.assertEqual(own, {'0': 'screens/test-sign-in/01-welcome.gif', '1': 'screens/test-sign-up/01-welcome.gif'})
        self.assertNotIn('data-own', home)  # Only Sign in walks it, so its one picture is already shown.
        self.assertIn('<option value="1" data-title="Sign up">', self.page())  # The large view names the flow it plays.
        # A list that a reload brings back picked would name one flow over another's clip: the page applies a pick only when it changes.
        self.assertIn('<select id="flow" autocomplete="off">', self.page())
        self.assertEqual(self.shown(), ['screens/test-sign-in/01-welcome.gif', 'screens/test-sign-in/02-home.png',
                                        'screens/test-sign-up/01-welcome.gif', 'screens/test-sign-up/02-setup.png'])


class ReadingARun(FlowMapTest):
    def test_a_step_is_named_after_its_file_with_its_rule_set_apart(self):
        walk(self.pictures, 'test-sign-in', ['welcome', 'ident-002-the-email-screen-asks-for-the-email'])

        draw(self.pictures, self.map)

        names = [step['name'] for step in self.flows()['test-sign-in']['steps']]
        self.assertEqual(names, ['Welcome', 'IDENT-002: the email screen asks for the email'])
        self.assertEqual(self.flows()['test-sign-in']['title'], 'Sign in')
        self.assertIn('<span class="rule">IDENT-002</span><span class="name">the email screen asks for the email</span>',
                      self.page())

    def test_flow_json_gives_the_exact_names_and_the_outcome(self):
        told = {'title': "Sign in, when the passkey sheet is closed", 'outcome': 'failed',
                'steps': [{'name': 'Welcome', 'picture': '01-welcome.png'},
                          {'name': "IDENT-024: the email screen says the prompt wasn't finished",
                           'picture': '02-ident-024-the-email-screen-says-the-prompt-wasn-t-finished.png'}]}
        walk(self.pictures, 'test-sign-in-closed',
             ['welcome', 'ident-024-the-email-screen-says-the-prompt-wasn-t-finished'], told=told)

        draw(self.pictures, self.map)

        page = self.page()
        self.assertIn('the email screen says the prompt wasn&#x27;t finished', page)
        self.assertIn('<figure class="screen stopped"', page)
        self.assertIn('<li class="failed" title="✗ Sign in, when the passkey sheet is closed">', page)

    def test_a_step_with_a_clip_shows_the_clip(self):
        walk(self.pictures, 'test-sign-in', ['welcome', 'home'], clips=['welcome'])

        draw(self.pictures, self.map)

        self.assertEqual(self.shown(), ['screens/test-sign-in/01-welcome.gif', 'screens/test-sign-in/02-home.png'])
        for picture in self.shown():
            self.assertTrue((self.map / picture).is_file())

    def test_steps_keep_the_order_of_their_numbers_past_nine(self):
        walk(self.pictures, 'test-long', [f'step-{letter}' for letter in 'abcdefghijk'])

        draw(self.pictures, self.map)

        names = [step['name'] for step in self.flows()['test-long']['steps']]
        self.assertEqual(names[8:], ['Step i', 'Step j', 'Step k'])

    def test_a_folder_without_flows_leaves_the_map_as_it_is(self):
        walk(self.pictures, 'test-sign-in', ['welcome'])
        draw(self.pictures, self.map)
        before = self.page()
        empty = self.pictures.parent / 'empty'
        (empty / 'setup').mkdir(parents=True)

        out = draw(empty, self.map, '--all', fails=True)

        self.assertIn('holds no flow, so the map is unchanged', out)
        self.assertEqual(self.page(), before)


class KeepingTheMap(FlowMapTest):
    def second_run(self):
        later = self.pictures.parent / 'later'
        later.mkdir()
        return later

    def test_a_later_run_adds_its_flows_and_keeps_the_earlier_ones(self):
        walk(self.pictures, 'test-sign-in', ['welcome', 'home'])
        draw(self.pictures, self.map, '--title', 'Shop Flow Map')
        later = self.second_run()
        walk(later, 'test-sign-up', ['welcome', 'setup'])

        out = draw(later, self.map)

        self.assertEqual(sorted(self.flows()), ['test-sign-in', 'test-sign-up'])
        self.assertIn('New: Sign up', out)
        self.assertIn('Kept from earlier runs: 1 flow\n', out)
        self.assertIn('<title>Shop Flow Map</title>', self.page())

    def test_a_flow_walked_again_gets_its_new_steps_and_pictures(self):
        walk(self.pictures, 'test-sign-in', ['welcome', 'lock', 'home'])
        draw(self.pictures, self.map)
        later = self.second_run()
        walk(later, 'test-sign-in', ['welcome', 'home'])

        out = draw(later, self.map)

        self.assertIn('Walked again: Sign in', out)
        self.assertEqual(sorted(file.name for file in (self.map / 'screens' / 'test-sign-in').iterdir()),
                         ['01-welcome.png', '02-home.png'])

    def test_after_a_run_of_every_flow_the_ones_it_did_not_walk_are_gone(self):
        walk(self.pictures, 'test-sign-in', ['welcome', 'home'])
        walk(self.pictures, 'test-renamed-since', ['welcome'])
        draw(self.pictures, self.map)
        later = self.second_run()
        walk(later, 'test-sign-in', ['welcome', 'home'])

        out = draw(later, self.map, '--all')

        self.assertEqual(list(self.flows()), ['test-sign-in'])
        self.assertIn('Gone: Renamed since', out)
        self.assertFalse((self.map / 'screens' / 'test-renamed-since').exists())

    def test_the_report_names_the_page_that_is_already_published(self):
        walk(self.pictures, 'test-sign-in', ['welcome'])
        self.map.mkdir()
        (self.map / 'link.txt').write_text('https://example.com/flow-map\n')

        out = draw(self.pictures, self.map)

        self.assertIn('Published at https://example.com/flow-map: update that page.', out)


if __name__ == '__main__':
    unittest.main()
