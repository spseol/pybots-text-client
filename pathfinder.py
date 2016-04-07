from pprint import pprint
from random import shuffle

from requests import get, post


EMPTY = 0
TREASURE = 1
BOT = 2
BLOCK = 3
LASER_BATTERY_BOT = 4

NORTH = 0
EAST = 1
SOUTH = 2
WEST = 3

post('http://localhost:44822/admin',
     dict(
         map_height=5, map_width=5,
         bots=1, treasures=1, blocks=25
     ))
bot_id = get('http://localhost:44822/init').json().get('bot_id')
game_map = get('http://localhost:44822/game/{}'.format(bot_id)).json().get('map')


def compute_orientation_price(start_orientation, wanted_orientation):
    length = abs(wanted_orientation - start_orientation)
    assert 0 <= length <= 3
    return length if length < 3 else 1


def get_orientation_position_to_position(from_position, to_position):
    if from_position[0] == to_position[0] and from_position[1] == to_position[1] + 1:
        return SOUTH
    elif from_position[0] == to_position[0] and from_position[1] == to_position[1] - 1:
        return NORTH
    elif from_position[0] == to_position[0] + 1 and from_position[1] == to_position[1]:
        return EAST
    elif from_position[0] == to_position[0] - 1 and from_position[1] == to_position[1]:
        return WEST
    else:
        assert False


def get_available_closest_positions(position, game_map):
    available_closest_positions = []
    for possible_position in (
            (position[0], position[1] + 1),
            (position[0], position[1] - 1),
            (position[0] + 1, position[1]),
            (position[0] - 1, position[1])
    ):
        try:
            game_map[possible_position]
        except IndexError:
            pass
        else:
            available_closest_positions.append(possible_position)
    return available_closest_positions


def get_field_occurrences(field_type):
    found = []
    for x, column in enumerate(game_map):
        for y, field in enumerate(column):
            if field.get('field') == field_type:
                found.append((x, y))
    return found


class Map(tuple):
    def __getitem__(self, position):
        assert hasattr(position, '__iter__') and len(position) == 2
        if not all(map(lambda x: x >= 0, position)):
            raise IndexError
        return super().__getitem__(position[0])[position[1]]


def get_path(game_map, start_bot_position, start_orientation):
    treasures = get_field_occurrences(TREASURE)

    def rate_game_map(game_map, position=start_bot_position, orientation=start_orientation):
        game_map[start_bot_position].update(dict(price=0))
        price = 1

        def inner(price=price, position=position):
            available_positions = get_available_closest_positions(position, game_map)
            shuffle(available_positions)
            for new_position in available_positions:
                field = game_map[new_position]
                assert isinstance(field, dict)

                if 'price' not in field or field.get('price') > price:
                    field.update(dict(price=price))
                    # new_orientation = get_orientation_position_to_position(position, new_position)
                    # orientation_price = compute_orientation_price(orientation, new_orientation)
                    new_price = price + 1

                    inner(price=new_price, position=new_position)

        inner()
        return game_map

    rate_game_map(game_map, start_bot_position)
    pprint(list(list(field.get('price') for field in row) for row in game_map))


get_path(Map(game_map), (4, 4), NORTH)



