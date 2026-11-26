"""Tests of how a step's clip is cut, on made-up recordings. They need only Python 3."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

from clip_cut import plan  # noqa: E402
from recording import Frame, Recording, Touch  # noqa: E402


def recording(frames, touches=(), keys=(), pauses=()):
    """Frames as (time, screen). Screens `home~1` and `home~2` differ by a blinking cursor, `home` and `sheet` a lot."""
    return Recording(frames=[Frame(at, Path(screen)) for at, screen in frames], pauses=list(pauses),
                     touches=list(touches), keys=list(keys), end=frames[-1][0])


def share_of(made):
    """`home` and `sheet` differ a lot, `home~1` and `home~2` by a blinking cursor, `home` and `home+banner` a little."""
    def share(first, second):
        before, after = made.frames[first].file.name, made.frames[second].file.name
        if before == after:
            return 0.0
        if before.split('+')[0] != after.split('+')[0]:
            return 1.0 if before.split('~')[0] != after.split('~')[0] else 0.001
        return 0.02
    return share


def cut(made, start, end):
    return plan(start, end, made, share_of(made))


def tap(at, x=10, y=20):
    return Touch(at, (x, y), (x, y))


def screens(made, shots):
    return [made.frames[frame].file.name for _, frame, _, _ in shots]


def length(shots):
    return sum(ms for _, _, _, ms in shots)


class WhatAClipShows(unittest.TestCase):
    def test_a_step_where_nothing_happens_has_no_clip(self):
        made = recording([(0, 'home~1'), (0.5, 'home~2'), (1.0, 'home~1')])

        self.assertIsNone(cut(made, 0, 1.5))

    def test_a_clip_runs_from_the_steps_picture_to_the_next_steps_picture(self):
        made = recording([(0, 'email'), (1.0, 'sheet')], touches=[tap(0.6)])

        shots = cut(made, 0, 1.2)

        self.assertEqual(screens(made, shots)[0], 'email')
        self.assertEqual(screens(made, shots)[-1], 'sheet')
        self.assertEqual(shots[0], (None, 0, None, 400))
        self.assertEqual(shots[-1], (None, 1, None, 600))

    def test_a_small_change_that_stays_gets_a_clip(self):
        made = recording([(0, 'home~1'), (2.0, 'home+banner'), (2.6, 'home+banner')])

        shots = cut(made, 0, 2.6)

        self.assertEqual(screens(made, shots)[-1], 'home+banner')
        self.assertEqual(screens(made, shots)[0], 'home~1')

    def test_a_clip_never_shows_a_frame_from_after_the_next_steps_picture(self):
        made = recording([(0, 'form'), (0.6, 'next screen')], keys=[0.2])

        shots = cut(made, 0, 0.56)

        self.assertNotIn('next screen', screens(made, shots))

    def test_a_typed_key_counts_as_something_happening(self):
        made = recording([(0, 'form~1'), (0.5, 'form~2')], keys=[0.5])

        self.assertIsNotNone(cut(made, 0, 1.0))

    def test_the_screen_changing_by_itself_counts_too(self):
        made = recording([(0, 'home'), (3.0, 'home, verified')])

        self.assertEqual(screens(made, cut(made, 0, 3.5))[-1], 'home, verified')


class CuttingTheWaits(unittest.TestCase):
    def test_the_seconds_between_what_happens_are_cut(self):
        spinner = [(0.1 * tick, f'wait~{tick}') for tick in range(10, 190)]
        made = recording([(0, 'wait~0')] + spinner + [(19.5, 'home')], touches=[tap(1.0)])

        shots = cut(made, 0, 20.0)

        # Kept: 0 to 2.0 around the start and the tap, and 19.2 to 20.0 around the new screen: 30 tenths.
        self.assertEqual(length(shots), 30 * 100 + 400 + 600)
        self.assertNotIn('wait~100', screens(made, shots))

    def test_a_long_clip_keeps_its_start_and_its_end(self):
        frames = [(float(second), f'screen {second}') for second in range(13)]
        made = recording(frames, touches=[tap(float(second)) for second in range(13)])

        shots = cut(made, 0, 12.0)

        self.assertEqual(length(shots), 6000)
        self.assertEqual(screens(made, shots)[0], 'screen 0')
        self.assertEqual(screens(made, shots)[-1], 'screen 12')
        self.assertNotIn('screen 6', screens(made, shots))

    def test_after_a_pause_the_clip_goes_on_with_the_next_frame(self):
        made = recording([(0, 'form'), (2.5, 'signed in')], touches=[tap(0.5), tap(2.6)], pauses=[1.0])

        shots = cut(made, 0, 3.0)

        self.assertEqual(length(shots), (10 + 6) * 100 + 400 + 600)  # 0 to 0.9, then 2.5 to 3.0


class TheFinger(unittest.TestCase):
    def finger_at(self, touches, time):
        made = recording([(0, 'screen'), (3.0, 'next')], touches=touches)
        for at, _, place, _ in cut(made, 0, 3.0):
            if at is not None and abs(at - time) < 0.05:
                return place and tuple(round(value, 6) for value in place)
        raise AssertionError(f'no tenth at {time}')

    def test_it_shows_from_just_before_the_touch_until_just_after(self):
        touches = [tap(1.0)]

        self.assertIsNone(self.finger_at(touches, 0.6))
        self.assertEqual(self.finger_at(touches, 0.8), (10, 20))
        self.assertEqual(self.finger_at(touches, 1.1), (10, 20))
        self.assertIsNone(self.finger_at(touches, 1.3))

    def test_it_moves_along_a_swipe(self):
        swipe = Touch(1.0, (0, 0), (100, 0), 0.4)

        self.assertEqual(self.finger_at([swipe], 1.2), (50.0, 0.0))

    def test_of_two_close_touches_the_nearer_one_shows(self):
        touches = [tap(1.0, x=1), tap(1.3, x=2)]

        self.assertEqual(self.finger_at(touches, 1.1)[0], 1)
        self.assertEqual(self.finger_at(touches, 1.2)[0], 2)

    def test_a_touch_shows_only_in_the_step_where_it_lands(self):
        made = recording([(0, 'screen'), (1.0, 'next')], touches=[tap(0.2), tap(1.1, x=99)])

        shots = cut(made, 0, 1.0)

        self.assertNotIn((99, 20), [place for _, _, place, _ in shots])


if __name__ == '__main__':
    unittest.main()
