"""The pictures side of the clips: reading frames, telling a move, drawing a finger, and saving GIFs."""
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw

CLIP_BOX = 800, 800         # a clip's frames fit inside this, and are never made larger
CHANGED_BY = 24             # a pixel of a small copy changed when one of its colours differs by more than this


def fitted(image, box):
    scale = min(box[0] / image.width, box[1] / image.height, 1.0)
    size = max(1, round(image.width * scale)), max(1, round(image.height * scale))
    return image if size == image.size else image.resize(size, Image.Resampling.LANCZOS)


class Frames:
    """A recording's frames, read when a clip needs them."""

    def __init__(self, recording):
        self.files = [frame.file for frame in recording.frames]
        self.full = lru_cache(maxsize=48)(self._full)
        self.small = lru_cache(maxsize=256)(self._small)

    def _full(self, number):
        with Image.open(self.files[number]) as image:
            return fitted(image.convert('RGB'), CLIP_BOX)

    def _small(self, number):
        """A small copy, a tenth as wide, so a blinking cursor counts for little."""
        image = self.full(number)
        return image.resize((max(1, image.width // 10), max(1, image.height // 10)), Image.Resampling.BOX)

    def share(self, first, second):
        """How much of the screen differs between two frames, from 0 to 1.

        Colour by colour, not in grey: a banner that turns from orange to green keeps its brightness.
        """
        before, after = self.small(first), self.small(second)
        if before.size != after.size:
            return 1.0
        red, green, blue = ImageChops.difference(before, after).split()
        most = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        changed = most.point(lambda value: 255 if value > CHANGED_BY else 0)
        return changed.histogram()[255] / (changed.width * changed.height)


def with_finger(image, place):
    """A dot where the finger is, with a dark edge and a light halo, so it shows on light and dark screens."""
    radius = max(7, round(image.width * 0.016))
    x, y = place
    layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    halo = radius + 4
    draw.ellipse((x - halo, y - halo, x + halo, y + halo), fill=(255, 255, 255, 150))
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(50, 50, 50, 120),
                 outline=(15, 15, 15, 235), width=2)
    return Image.alpha_composite(image.convert('RGBA'), layer).convert('RGB')


def one_palette(base, others):
    """One palette for a whole GIF, from the base picture and a small copy of every other picture.

    Fast octree, not median cut: median cut spends most colours on large white and grey areas, so a small bright
    button turns grey-blue. A screen that shows only inside a clip still gives its colours.
    """
    smalls = [image.resize((max(1, image.width // 4), max(1, image.height // 4))) for image in others]
    width = max([base.width] + [small.width for small in smalls])
    rows, row, x, row_height = [], [], 0, 0
    for small in smalls:
        if row and x + small.width > width:
            rows.append((row, row_height))
            row, x, row_height = [], 0, 0
        row.append((x, small))
        x, row_height = x + small.width, max(row_height, small.height)
    if row:
        rows.append((row, row_height))
    mosaic = Image.new('RGB', (width, base.height + sum(height for _, height in rows)), (255, 255, 255))
    mosaic.paste(base, (0, 0))
    y = base.height
    for row, height in rows:
        for x, small in row:
            mosaic.paste(small, (x, y))
        y += height
    return mosaic.quantize(256, method=Image.Quantize.FASTOCTREE)


def save_gif(path, pictures, palette):
    """A looping GIF of (picture, milliseconds), all on one palette and without dithering.

    Then two frames differ only where the screen changed, and the GIF stores only that part.
    """
    frames = [picture.quantize(palette=palette, dither=Image.Dither.NONE) for picture, _ in pictures]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=[length for _, length in pictures],
                   loop=0, optimize=False)
