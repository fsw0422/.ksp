"""Draw each flow's clips and sheets from the step pictures and the recording that its test left.

  uv run --no-project --with pillow python -I flow_sheets.py <pictures folder, or one flow's folder>

Beside each flow's step pictures, it writes a clip for each step where something happens, such as
`02-the-email-screen.gif`, the still sheet `flow.png`, and, when a step has a clip, the moving sheet `flow.gif`.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # so `python -I` finds the modules beside this file

try:
    from PIL import Image
except ImportError:
    sys.exit('Pillow is missing. Run this script with `uv run --no-project --with pillow python -I ...`.')

from clip_cut import joined, plan  # noqa: E402
from pictures import Frames, fitted, one_palette, save_gif, with_finger  # noqa: E402
from recording import read_recording  # noqa: E402
from sheets import Sheet  # noqa: E402


def flows_in(folder):
    if (folder / 'flow.json').is_file():
        return [folder]
    return sorted(child for child in folder.iterdir() if (child / 'flow.json').is_file())


def draw_flow(folder):
    """Draw one flow. The still sheet comes first, so an error in a clip costs no more than that clip."""
    told = json.loads((folder / 'flow.json').read_text(encoding='utf-8'))
    title = told.get('title') or folder.name
    steps = [step for step in told.get('steps', []) if (folder / Path(step['picture']).name).is_file()]
    if not steps:
        return [f'{title}: no step pictures, so nothing to draw']
    stills = [read(folder / Path(step['picture']).name) for step in steps]
    sheet = Sheet(title, told.get('outcome'), [step['name'] for step in steps], stills[0].size)
    still = sheet.still(stills)
    still.save(folder / 'flow.png', optimize=True)
    notes = []
    clips = cut_clips(folder, told, steps, notes, sheet.tile)
    if any(clips):
        try:
            base, frames = sheet.moving(still, clips)
            save_gif(folder / 'flow.gif', frames, one_palette(base, [picture for clip in clips if clip
                                                                     for picture, _ in clip]))
        except Exception as error:  # noqa: BLE001 - the still sheet and the clips stay
            notes.append(f'no moving sheet: {error}')
    return [summary(folder, title, steps, clips)] + [f'  {note}' for note in notes]


def cut_clips(folder, told, steps, notes, tile):
    """Each step's clip, saved beside the step's picture, and kept at the sheet's size as (picture, milliseconds).

    A step without a clip gets None.
    """
    recording = read_recording(folder)
    if recording is None:
        return [None] * len(steps)
    notes.extend(recording.problems)
    if not recording.frames:
        notes.append('the recording holds no frame, so no clips')
        return [None] * len(steps)
    if any('at' not in step for step in steps):
        notes.append('flow.json gives no time for each step, so no clips')
        return [None] * len(steps)
    frames = Frames(recording)
    scale = scale_of(told, frames)
    ends = [step['at'] for step in steps[1:]] + [recording.end]
    clips = []
    for step, end in zip(steps, ends):
        clip = cut_one(folder, step, end, recording, frames, scale, notes)
        clips.append([(fitted(picture, tile), length) for picture, length in clip] if clip else None)
    return clips


def cut_one(folder, step, end, recording, frames, scale, notes):
    if recording.lost and end > recording.lost[0]:
        notes.append(f'no clip for "{step["name"]}": the stream broke in it: {recording.lost[1]}')
        return None
    try:
        shots = plan(step['at'], end, recording, frames.share)
        if not shots:
            return None
        clip = [(picture_of(frames, frame, place, scale), length) for frame, place, length in joined(shots)]
        save_gif(folder / Path(step['picture']).with_suffix('.gif').name, clip,
                 one_palette(clip[0][0], [picture for picture, _ in clip]))
        return clip
    except Exception as error:  # noqa: BLE001 - the other clips stay
        notes.append(f'no clip for "{step["name"]}": {error}')
        return None


def scale_of(told, frames):
    """From the screen's units, such as CSS pixels, to the clip's pixels."""
    screen = told.get('screen')
    return frames.full(0).width / screen[0] if screen else 1.0


def picture_of(frames, frame, place, scale):
    picture = frames.full(frame)
    return with_finger(picture, (place[0] * scale, place[1] * scale)) if place else picture


def read(path):
    with Image.open(path) as image:
        return image.convert('RGB')


def summary(folder, title, steps, clips):
    made = [clip for clip in clips if clip]
    line = f'{title}: {len(steps)} steps, {len(made)} with a clip. {folder / "flow.png"}'
    if made:
        lengths = [sum(length for _, length in clip) / 1000 for clip in made]
        line += f', {folder / "flow.gif"} ({size_of(folder / "flow.gif")}). Clips {min(lengths):.1f}-{max(lengths):.1f} s'
    return line


def size_of(path):
    if not path.is_file():
        return 'not drawn'
    size = path.stat().st_size
    return f'{size / 1_000_000:.1f} MB' if size >= 1_000_000 else f'{max(1, round(size / 1000))} KB'


def main():
    parser = argparse.ArgumentParser(description="Draw each flow's clips and sheets from its pictures and recording.")
    parser.add_argument('folder', help="a run's pictures folder, with a folder for each flow, or one flow's folder")
    folder = Path(parser.parse_args().folder).resolve()
    if not folder.is_dir():
        sys.exit(f'{folder} is not a folder.')
    flows = flows_in(folder)
    if not flows:
        sys.exit(f'{folder} holds no flow.json, so there is nothing to draw.')
    for flow in flows:
        print('\n'.join(draw_flow(flow)))


if __name__ == '__main__':
    main()
