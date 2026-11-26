"""Read what a flow's recorder left in its `recording` folder: the frames, when each was drawn, and the inputs."""
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Frame:
    at: float
    file: Path


@dataclass
class Touch:
    """A tap, or a swipe from one place to another, in the screen's own units, such as CSS pixels."""
    at: float
    place: tuple
    to: tuple
    seconds: float = 0.0

    def where(self, time):
        """Where the finger is at that time: along a swipe, it moves from its start to its end."""
        if self.seconds <= 0 or time <= self.at:
            return self.place
        part = min(1.0, (time - self.at) / self.seconds)
        return tuple(start + (end - start) * part for start, end in zip(self.place, self.to))


@dataclass
class Recording:
    frames: list = field(default_factory=list)
    pauses: list = field(default_factory=list)    # when frames were left out on purpose, such as for a secret
    lost: tuple = None                            # when and why the stream broke: nothing is known after it
    end: float = None                             # when the recording ended
    touches: list = field(default_factory=list)
    keys: list = field(default_factory=list)      # when the test typed: no finger, but something happens
    problems: list = field(default_factory=list)


def read_recording(flow_folder):
    """The flow's recording, or None when its test recorded none, such as with clips off."""
    folder = flow_folder / 'recording'
    if not (folder / 'frames.jsonl').is_file():
        return None
    recording = Recording()
    for line in lines(folder / 'frames.jsonl', recording.problems):
        take_frame_line(recording, folder, line)
    for line in lines(folder / 'inputs.jsonl', recording.problems):
        take_input_line(recording, line)
    recording.frames.sort(key=lambda frame: frame.at)
    if recording.end is None and recording.frames:
        recording.end = recording.frames[-1].at
    return recording


def take_frame_line(recording, folder, line):
    at = float(line['at'])
    if 'frame' in line:
        recording.frames.append(Frame(at, folder / Path(line['frame']).name))
    elif 'pause' in line:
        recording.pauses.append(at)
    elif 'lost' in line and recording.lost is None:
        recording.lost = at, line['lost']
    elif 'end' in line:
        recording.end = at


def take_input_line(recording, line):
    at, kind = float(line['at']), line.get('kind')
    if kind == 'tap':
        recording.touches.append(Touch(at, tuple(line['place']), tuple(line['place'])))
    elif kind == 'swipe':
        recording.touches.append(Touch(at, tuple(line['place']), tuple(line['to']), line.get('ms', 300) / 1000))
    elif kind == 'key':
        recording.keys.append(at)


def lines(file, problems):
    """Each line of a JSON Lines file. A test that crashed can leave its last line half written."""
    if not file.is_file():
        return []
    found = []
    for number, text in enumerate(file.read_text(encoding='utf-8').splitlines(), 1):
        if not text.strip():
            continue
        try:
            found.append(json.loads(text))
        except json.JSONDecodeError:
            problems.append(f'{file.name} line {number} is not JSON, so it was left out')
    return found
