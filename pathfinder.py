from requests import get

EMPTY = 0
TREASURE = 1
BOT = 2
BLOCK = 3
LASER_BATTERY_BOT = 4

bot_id = get('http://localhost:44822/init').json().get('bot_id')
game_map = get('http://localhost:44822/game/{}'.format(bot_id)).json().get('map')


class Map(tuple):
    def __getitem__(self, position):
        assert hasattr(position, '__iter__') and len(position) == 2
        return super().__getitem__(position[0])[position[1]]


def get_path(game_map, start_bot_position):
    def get_field_occurrences(field_type):
        found = []
        for x, column in enumerate(game_map):
            for y, field in enumerate(column):
                if field.get('field') == field_type:
                    found.append((x, y))
        return found

    treasures = get_field_occurrences(TREASURE)

    def rate_game_map(game_map):
        return game_map


get_path(Map(game_map), None)
