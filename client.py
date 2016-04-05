import curses as c
from time import sleep

from requests import get, post

SERVER_NAME = 'hroch.spseol.cz:44822'
SERVER_NAME = 'localhost:44822'


class MapCursesRenderer(object):
    def __init__(self, screen):
        super().__init__()
        c.init_pair(1, c.COLOR_BLACK, c.COLOR_BLACK)
        c.init_pair(2, c.COLOR_YELLOW, c.COLOR_YELLOW)
        c.init_pair(3, c.COLOR_RED, c.COLOR_RED)
        c.init_pair(4, c.COLOR_BLUE, c.COLOR_BLUE)
        c.init_pair(5, c.COLOR_RED, c.COLOR_RED)
        self.main_screen = screen.subwin(0, 0)
        self.main_screen.border(0)

        self.map_caption_screen = None
        self.game_map_screen = None

    def refresh_game_map(self, game_map):
        map_caption = '/'.join((SERVER_NAME, 'game', str(bot_id)))

        self.map_caption_screen = self.main_screen.subwin(3, len(map_caption) + 2, 1, 1)
        self.map_caption_screen.border(0)
        self.map_caption_screen.addstr(1, 1, map_caption)

        self.game_map_screen = screen.subwin(len(game_map) + 2, len(game_map[0]) + 2, 4, 1)
        self.game_map_screen.border(0)

    def render(self, game_map):
        if not self.game_map_screen:
            raise Exception('Call refresh_game_map before first render.')

        for x, column in enumerate(game_map):
            for y, field in enumerate(column):
                field_type = field.get('field')
                self.game_map_screen.addstr(x + 1, y + 1, str(field_type), c.color_pair(field_type + 1))

        self.game_map_screen.refresh()


post('http://{}/admin'.format(SERVER_NAME),
     dict(
         map_height=15, map_width=30,
         bots=1, treasures=1, blocks=25, maze_game=True,
         # rounded_game=False, battery_game=False, laser_game=False
     ))
input('Please, now connect client.')
games = get('http://{}/list'.format(SERVER_NAME)).json().get('games')

if len(games) < 1:
    raise Exception('No client connected.')

bot_id = games[0].get('bot_id')

try:
    screen = c.initscr()
    c.start_color()
    c.noecho()
    game_map = get('http://{}/game/{}'.format(SERVER_NAME, bot_id)).json().get('map')

    renderer = MapCursesRenderer(screen)
    renderer.refresh_game_map(game_map)
    while True:
        renderer.render(game_map)
        game_map = get('http://{}/game/{}'.format(SERVER_NAME, bot_id)).json().get('map')
        sleep(1)


    screen.getch()
finally:
    c.endwin()