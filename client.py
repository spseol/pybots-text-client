import curses as c

from requests import get, post

SERVER_NAME = 'hroch.spseol.cz:44822'
# SERVER_NAME = 'localhost:44822'

post('http://{}/admin'.format(SERVER_NAME),
     dict(map_height=10, map_width=10, bots=1, treasures=1, blocks=25, rounded_game=False, battery_game=False,
          laser_game=False))
bot_id = get('http://{}/init'.format(SERVER_NAME)).json().get('bot_id')

game_map = get('http://{}/game/{}'.format(SERVER_NAME, bot_id)).json().get('map')

try:
    screen = c.initscr()
    c.start_color()
    c.noecho()

    main_screen = screen.subwin(0, 0)
    main_screen.border(0)
    server_name_screen = screen.subwin(3, len(SERVER_NAME) + 2, 1, 1)
    server_name_screen.border(0)
    server_name_screen.addstr(1, 1, SERVER_NAME)

    c.init_pair(1, c.COLOR_BLACK, c.COLOR_BLACK)
    c.init_pair(2, c.COLOR_YELLOW, c.COLOR_YELLOW)
    c.init_pair(3, c.COLOR_RED, c.COLOR_RED)
    c.init_pair(4, c.COLOR_BLUE, c.COLOR_BLUE)
    c.init_pair(5, c.COLOR_RED, c.COLOR_RED)

    game_map_screen = screen.subwin(len(game_map) + 2, len(game_map[0]) + 2, 4, 1)
    game_map_screen.border(0)
    for x, column in enumerate(game_map):
        for y, field in enumerate(column):
            field_type = field.get('field')
            game_map_screen.addstr(x + 1, y + 1, str(field_type), c.color_pair(field_type + 1))

    screen.refresh()

    screen.getch()
finally:
    c.endwin()
