"""Join flows into trees of screens, and give each screen its place.

Two flows share a screen while they have walked the same step names from their start. The same name
later, on another path, is another screen: "The sheet opens again" can follow a sign-up and a sign-in.
"""


class Screen:
    def __init__(self, name, depth):
        self.name = name
        self.depth = depth  # how many steps lead here
        self.row = 0.0      # its place among the screens of the same depth
        self.picture = None
        self.walked = ''
        self.flows = []     # the flows that walk through it, by number
        self.ends = []      # the flows that end here
        self.next = {}      # the screens that follow, by step name


def join(flows):
    """The start screens of the flows. Screens are drawn in the order the flows are given."""
    starts = {}
    for number, flow in enumerate(flows):
        following, screen = starts, None
        for depth, step in enumerate(flow['steps']):
            if step['name'] not in following:
                following[step['name']] = Screen(step['name'], depth)
            screen = following[step['name']]
            screen.flows.append(number)
            if flow['walked'] >= screen.walked:  # the picture comes from the flow that was walked last
                screen.picture, screen.walked = step['picture'], flow['walked']
            following = screen.next
        screen.ends.append(number)
    return list(starts.values())


BETWEEN_STARTS = 0.15  # of a row: the gap that sets flows with different start screens apart


def place(starts):
    """Give each screen its row, and return how many rows the map is high.

    A screen that nothing follows takes the next free row. Any other stands midway between the first
    and the last screen that follow it, so its arrows fan out evenly.
    """
    rows = 0.0

    def settle(screen):
        nonlocal rows
        if screen.next:
            following = [settle(follower) for follower in screen.next.values()]
            screen.row = (following[0] + following[-1]) / 2
        else:
            screen.row = rows
            rows += 1
        return screen.row

    for start in starts:
        settle(start)
        rows += BETWEEN_STARTS
    return rows - BETWEEN_STARTS


def each(screens):
    """Every screen, each before the screens that follow it."""
    for screen in screens:
        yield screen
        yield from each(screen.next.values())
