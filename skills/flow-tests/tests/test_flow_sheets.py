"""Tests of the clips and sheets script, on made-up runs in throwaway folders. They need Pillow:

  uv run --no-project --with pillow python -m unittest discover -s <this skill's folder>/tests
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

SCRIPT = Path(__file__).resolve().parent.parent / 'scripts' / 'flow_sheets.py'
SCREEN = 640, 360
COLOURS = {'welcome': (240, 240, 240), 'email': (190, 190, 150), 'sheet': (40, 90, 200),
           'orange': (253, 231, 200), 'green': (201, 240, 216)}


def screen(name, size=SCREEN):
    return Image.new('RGB', size, COLOURS[name])


class Run:
    """A flow's folder the way a test leaves it: step pictures, flow.json, and a recording."""

    def __init__(self, folder, title='Sign up', outcome='passed'):
        self.folder = folder
        folder.mkdir(parents=True)
        self.told = {'title': title, 'outcome': outcome, 'screen': list(SCREEN), 'steps': []}
        self.frames, self.inputs = [], []

    def step(self, name, at, picture):
        file = f'{len(self.told["steps"]) + 1:02d}-{name}.png'
        screen(picture).save(self.folder / file)
        self.told['steps'].append({'name': name.capitalize(), 'picture': file, 'at': at})

    def frame(self, at, picture):
        (self.folder / 'recording').mkdir(exist_ok=True)
        file = f'{len(self.frames) + 1:05d}.png'
        screen(picture, (SCREEN[0] // 2, SCREEN[1] // 2)).save(self.folder / 'recording' / file)
        self.frames.append({'at': at, 'frame': file})

    def line(self, **line):
        self.frames.append(line)

    def tap(self, at, x, y):
        self.inputs.append({'at': at, 'kind': 'tap', 'place': [x, y]})

    def save(self):
        (self.folder / 'flow.json').write_text(json.dumps(self.told))
        if self.frames:
            write_lines(self.folder / 'recording' / 'frames.jsonl', self.frames)
            write_lines(self.folder / 'recording' / 'inputs.jsonl', self.inputs)


def write_lines(file, lines):
    file.write_text(''.join(json.dumps(line) + '\n' for line in lines))


def draw(folder):
    done = subprocess.run([sys.executable, '-I', str(SCRIPT), str(folder)], capture_output=True, text=True)
    if done.returncode != 0:
        raise AssertionError(done.stdout + done.stderr)
    return done.stdout


def near(colour, name):
    """One palette for a whole GIF moves a colour a little."""
    return max(abs(got - wanted) for got, wanted in zip(colour, COLOURS[name])) <= 16


def frames_of(gif):
    with Image.open(gif) as image:
        found = []
        for number in range(image.n_frames):
            image.seek(number)
            found.append((image.convert('RGB'), image.info['duration']))
        return found


@unittest.skipIf(Image is None, 'needs Pillow: run the tests with `uv run --no-project --with pillow`')
class FlowSheetsTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.pictures = Path(temp.name).resolve() / 'pictures'

    def sign_up(self, **options):
        """Welcome, then a tap on the email screen brings up the sheet. Nothing happens on the sheet."""
        run = Run(self.pictures / 'test-sign-up', **options)
        run.step('welcome', 100.0, 'welcome')
        run.frame(99.9, 'welcome')
        run.frame(100.8, 'email')
        run.step('the-email-screen', 101.5, 'email')
        run.tap(102.0, 320, 300)
        run.frame(102.5, 'sheet')
        run.step('the-passkey-sheet', 103.0, 'sheet')
        run.line(at=104.0, end=True)
        return run


class DrawingAFlow(FlowSheetsTest):
    def test_each_step_where_something_happens_gets_a_clip_and_the_flow_gets_both_sheets(self):
        run = self.sign_up()
        run.save()

        out = draw(self.pictures)

        made = sorted(file.name for file in run.folder.glob('*.gif'))
        self.assertEqual(made, ['01-welcome.gif', '02-the-email-screen.gif', 'flow.gif'])
        self.assertTrue((run.folder / 'flow.png').is_file())
        self.assertIn('Sign up: 3 steps, 2 with a clip.', out)

    def test_a_clip_opens_on_the_steps_screen_and_ends_on_the_next(self):
        run = self.sign_up()
        run.save()

        draw(self.pictures)

        frames = frames_of(run.folder / '02-the-email-screen.gif')
        self.assertTrue(near(frames[0][0].getpixel((5, 5)), 'email'))
        self.assertTrue(near(frames[-1][0].getpixel((5, 5)), 'sheet'))
        self.assertGreaterEqual(frames[0][1], 400)
        self.assertGreaterEqual(frames[-1][1], 600)

    def test_a_tap_shows_as_a_dot_where_it_lands(self):
        run = self.sign_up()
        run.save()

        draw(self.pictures)

        # The clip is half the screen's size, so the tap at 320, 300 lands at 160, 150.
        middles = [picture.getpixel((160, 150)) for picture, _ in frames_of(run.folder / '02-the-email-screen.gif')]
        self.assertTrue(any(near(colour, 'email') for colour in middles))
        self.assertTrue(any(sum(colour) < sum(COLOURS['email']) - 150 for colour in middles))

    def test_the_still_sheet_puts_the_steps_side_by_side(self):
        run = self.sign_up()
        run.save()

        draw(self.pictures)

        with Image.open(run.folder / 'flow.png') as sheet:
            # Three wide pictures, 400 x 225 each, with 24 between them and around them.
            self.assertEqual(sheet.size, (24 + 3 * (400 + 24), 64 + 86 + 225 + 24))
            self.assertEqual(sheet.getpixel((24 + 2 * 424 + 200, 64 + 86 + 100)), COLOURS['sheet'])

    def test_a_failed_flow_marks_its_last_step(self):
        run = self.sign_up(outcome='failed')
        run.save()

        draw(self.pictures)

        with Image.open(run.folder / 'flow.png') as sheet:
            self.assertEqual(sheet.convert('RGB').getpixel((24 + 2 * 424 - 3, 64 + 86 + 100)), (179, 38, 30))

    def test_the_moving_sheet_plays_one_step_at_a_time(self):
        run = self.sign_up()
        run.save()

        draw(self.pictures)

        frames = frames_of(run.folder / 'flow.gif')
        tiles = [(picture.getpixel((24 + 200, 64 + 86 + 100)), picture.getpixel((24 + 424 + 200, 64 + 86 + 100)))
                 for picture, _ in frames]
        # The first step's clip reaches the email screen, while the second step waits on its own first frame.
        self.assertTrue(any(near(first, 'email') and near(second, 'email') for first, second in tiles))
        # Then the second step's clip reaches the sheet, while the first waits on its own first frame.
        self.assertTrue(any(near(first, 'welcome') and near(second, 'sheet') for first, second in tiles))


class TellingAChange(FlowSheetsTest):
    def test_a_banner_that_changes_colour_but_not_brightness_gets_a_clip(self):
        run = Run(self.pictures / 'test-verify')
        run.step('home-not-verified', 100.0, 'orange')
        run.frame(99.9, 'orange')
        run.frame(102.0, 'green')
        run.step('home-verified', 102.5, 'green')
        run.line(at=103.0, end=True)
        run.save()

        draw(self.pictures)

        self.assertTrue((run.folder / '01-home-not-verified.gif').is_file())


class WhatAClipLeavesOut(FlowSheetsTest):
    def test_a_broken_stream_costs_the_clips_from_then_on(self):
        run = self.sign_up()
        run.frames.insert(2, {'at': 101.0, 'lost': 'the stream ended by itself'})
        run.save()

        out = draw(self.pictures)

        self.assertFalse((run.folder / '01-welcome.gif').exists())
        self.assertFalse((run.folder / '02-the-email-screen.gif').exists())
        self.assertIn('no clip for "Welcome": the stream broke in it: the stream ended by itself', out)

    def test_a_flow_without_a_recording_gets_its_still_sheet_only(self):
        run = self.sign_up()
        run.frames = []
        run.save()

        out = draw(self.pictures)

        self.assertTrue((run.folder / 'flow.png').is_file())
        self.assertEqual(list(run.folder.glob('*.gif')), [])
        self.assertIn('Sign up: 3 steps, 0 with a clip.', out)

    def test_a_half_written_last_line_is_left_out_and_named(self):
        run = self.sign_up()
        run.save()
        with open(run.folder / 'recording' / 'frames.jsonl', 'a') as file:
            file.write('{"at": 104.5, "fra')

        out = draw(self.pictures)

        self.assertIn('frames.jsonl line 5 is not JSON, so it was left out', out)
        self.assertTrue((run.folder / 'flow.gif').is_file())


if __name__ == '__main__':
    unittest.main()
