import curses as c

from requests import get

SERVER_NAME = 'hroch.spseol.cz:44822+'
SERVER_NAME = 'localhost:44822'

bot_id = get('http://{}/init'.format(SERVER_NAME)).json().get('bot_id')

game_map = get('http://{}/game/{}'.format(SERVER_NAME, bot_id)).json().get('map')

try:
    screen = c.initscr()
    c.start_color()
    c.init_pair(1, c.COLOR_BLACK, c.COLOR_BLACK)
    c.init_pair(2, c.COLOR_YELLOW, c.COLOR_YELLOW)
    c.init_pair(3, c.COLOR_RED, c.COLOR_RED)
    c.init_pair(4, c.COLOR_BLUE, c.COLOR_BLUE)
    c.init_pair(5, c.COLOR_RED, c.COLOR_RED)

#     screen.subwin(len(game_map) + 2, len(game_map[0]) + 2, 9, 9).border(0)
    for x, column in enumerate(game_map):
        for y, field in enumerate(column):
            field_type = field.get('field')
            screen.addstr(10 + x, 10 + y, str(field_type), c.color_pair(field_type + 1))

    screen.refresh()

    screen.getch()
finally:
    c.endwin()
