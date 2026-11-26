"""Cut a step's clip: from its picture to the next step's picture, with the waits cut out.

This part only reasons about times. It says which frame shows when, with which finger, and for how long.
"""
TICK = 0.1                  # a clip shows the newest frame of each tenth of a second
MOVE_SHARE = 0.08           # a sheet, a keyboard or a new screen changes far more of a small copy; a spinner far less
CHANGED_SHARE = 0.005       # a screen that ends this different from how it started has a clip, such as a new banner
AROUND_INPUT = 0.5, 1.0     # the seconds kept before and after each input
AROUND_MOVE = 0.3, 0.7      # and around each move
AT_EACH_END = 0.5           # and at the step's own picture, and before the next step's picture
FIRST_HOLD, LAST_HOLD = 0.4, 0.6
LONGEST = 6.0               # a longer clip keeps its start and its end
DOT_BEFORE, DOT_AFTER = 0.3, 0.2


def plan(start, end, recording, share):
    """The clip as (time, frame number, finger place or None, milliseconds), or None when nothing happens.

    One shot for each tenth of a second it keeps, and a hold at each end, whose time is None.
    `share(a, b)` says how much of the screen differs between two frames, from 0 to 1.
    """
    touches = [touch for touch in recording.touches if start <= touch.at < end]
    keys = [at for at in recording.keys if start <= at < end]
    shown = ticks(start, end, recording.frames, recording.pauses)
    if not shown:
        return None
    moved = moves(shown, share)
    changed = shown[0][1] != shown[-1][1] and share(shown[0][1], shown[-1][1]) > CHANGED_SHARE
    if not (touches or keys or moved or changed):
        return None
    inputs = [touch.at for touch in touches] + keys
    chosen = capped(kept(shown, start, end, inputs, moved))
    shots = [(None, chosen[0][1], None, ms(FIRST_HOLD))]
    for time, frame in chosen:
        touch = finger(time, touches)
        shots.append((time, frame, touch.where(time) if touch else None, ms(TICK)))
    shots.append((None, chosen[-1][1], None, ms(LAST_HOLD)))
    return shots


def ticks(start, end, frames, pauses):
    """For each tenth of a second from start to end: the newest frame drawn by then, as (time, frame number).

    A frame from before a pause says nothing about the screen after it, so the clip goes on with the next frame.
    """
    times = [start + count * TICK for count in range(int((end - start) / TICK + 1e-6) + 1)]
    if end - times[-1] > 1e-6:
        times.append(end)  # the clip ends on the next step's picture
    shown, newest = [], -1
    for time in times:
        while newest + 1 < len(frames) and frames[newest + 1].at <= time:
            newest += 1
        if newest >= 0 and not any(frames[newest].at < pause <= time for pause in pauses):
            shown.append((time, newest))
    return shown


def moves(shown, share):
    """The times when much of the screen changed from one tenth to the next."""
    return [time for (_, before), (time, after) in zip(shown, shown[1:])
            if before != after and share(before, after) > MOVE_SHARE]


def kept(shown, start, end, inputs, moved):
    """The tenths around what happens: the step's picture, each input, each move, and the next picture."""
    windows = [(start, start + AT_EACH_END), (end - AT_EACH_END, end)]
    windows += [(at - AROUND_INPUT[0], at + AROUND_INPUT[1]) for at in inputs]
    windows += [(at - AROUND_MOVE[0], at + AROUND_MOVE[1]) for at in moved]
    return [tick for tick in shown if any(low - 1e-6 <= tick[0] <= high + 1e-6 for low, high in windows)]


def capped(chosen):
    """At most LONGEST seconds with the holds, by keeping the clip's start and its end."""
    room = int(round((LONGEST - FIRST_HOLD - LAST_HOLD) / TICK))
    if len(chosen) <= room:
        return chosen
    return chosen[:room // 2] + chosen[len(chosen) - (room - room // 2):]


def finger(time, touches):
    """The one finger to show: of the touches near that time, the nearest. None when no touch is near."""
    near = [touch for touch in touches if touch.at - DOT_BEFORE <= time <= touch.at + touch.seconds + DOT_AFTER]
    return min(near, key=lambda touch: away(time, touch), default=None)


def away(time, touch):
    if touch.at <= time <= touch.at + touch.seconds:
        return 0.0
    return min(abs(time - touch.at), abs(time - touch.at - touch.seconds))


def joined(shots):
    """Shots in a row that show the same frame with the same finger become one longer (frame, place, ms)."""
    runs = []
    for _, frame, place, length in shots:
        if runs and runs[-1][:2] == (frame, place):
            runs[-1] = (frame, place, runs[-1][2] + length)
        else:
            runs.append((frame, place, length))
    return runs


def ms(seconds):
    return int(round(seconds * 1000))
