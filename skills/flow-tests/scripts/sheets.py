"""A flow's sheets: its steps side by side under their names, still, and with each step's clip playing in turn."""
from PIL import Image, ImageDraw, ImageFont

from pictures import fitted

BOX = 400, 560              # the most room a picture takes: a browser window fills its width, a phone its height
GAP, TITLE, CAPTION = 24, 64, 86
PAPER, CARD, INK = (243, 245, 249), (255, 255, 255), (23, 28, 49)
FAILED, PLAYING = (179, 38, 30), (31, 79, 209)
NO_CLIP_TURN = 800          # how long a step without a clip keeps its turn on the moving sheet, in milliseconds


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:       # a Pillow older than 10.1 has only its small bitmap font
        return ImageFont.load_default()


class Sheet:
    def __init__(self, title, outcome, names, picture_size):
        width, height = picture_size
        scale = min(BOX[0] / width, BOX[1] / height)
        self.tile = round(width * scale), round(height * scale)
        self.title, self.outcome, self.names = title, outcome, names
        self.size = GAP + len(names) * (self.tile[0] + GAP), TITLE + CAPTION + self.tile[1] + GAP

    def place(self, number):
        """Where a step's picture goes on the sheet, counting steps from 0."""
        return GAP + number * (self.tile[0] + GAP), TITLE + CAPTION

    def still(self, pictures):
        """The still sheet: each step's picture under its name. A failed flow's last step is marked."""
        sheet = Image.new('RGB', self.size, PAPER)
        draw = ImageDraw.Draw(sheet)
        word = {'passed': 'passed', 'failed': 'failed'}.get(self.outcome)
        draw.text((GAP, 20), f'{self.title}{f" ({word})" if word else ""}', fill=INK, font=font(26))
        for number, (name, picture) in enumerate(zip(self.names, pictures)):
            x, y = self.place(number)
            caption(draw, f'{number + 1}. {name}', x, y, self.tile[0])
            self.paste(sheet, number, picture)
        if self.outcome == 'failed':
            self.outline(sheet, len(self.names) - 1, FAILED)
        return sheet

    def paste(self, sheet, number, picture):
        tile = Image.new('RGB', self.tile, CARD)
        shown = fitted(picture, self.tile)
        tile.paste(shown, ((self.tile[0] - shown.width) // 2, (self.tile[1] - shown.height) // 2))
        sheet.paste(tile, self.place(number))

    def outline(self, sheet, number, colour):
        x, y = self.place(number)
        ImageDraw.Draw(sheet).rectangle((x - 4, y - 4, x + self.tile[0] + 3, y + self.tile[1] + 3),
                                        outline=colour, width=3)

    def moving(self, still, clips):
        """The moving sheet: the steps play their clips one after another, from left to right.

        While one step plays, each other step shows the first frame of its own clip, so the eye can follow one.
        `clips` has a list of (picture, milliseconds) for each step, or None for a step without a clip.
        """
        base = still.copy()
        for number, clip in enumerate(clips):
            if clip:
                self.paste(base, number, clip[0][0])
        frames = []
        for number, clip in enumerate(clips):
            for picture, length in clip or [(None, NO_CLIP_TURN)]:
                frame = base.copy()
                if picture is not None:
                    self.paste(frame, number, picture)
                self.outline(frame, number, PLAYING)
                frames.append((frame, length))
        return base, frames


def caption(draw, text, x, bottom, width):
    """The step's name above its picture, in at most three lines."""
    face = font(17)
    rows = wrapped(draw, text, face, width, 3)
    y = bottom - 10 - len(rows) * 22
    for row in rows:
        draw.text((x, y), row, fill=INK, font=face)
        y += 22


def wrapped(draw, text, face, width, most):
    rows = ['']
    for word in text.split():
        trial = f'{rows[-1]} {word}'.strip()
        if not rows[-1] or draw.textlength(trial, font=face) <= width:
            rows[-1] = trial
        else:
            rows.append(word)
    if len(rows) > most:
        rows = rows[:most]
        rows[-1] = rows[-1].rstrip('.,;:') + '...'
    return rows
