from copy import deepcopy
from pprint import pprint

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

MAP_HEIGHT = 15
MAP_WIDTH = 12

print(post('http://localhost:44822/admin',
           dict(
               map_height=MAP_HEIGHT, map_width=MAP_WIDTH,
               bots=1, treasures=1, blocks=25
           )))
bot_id = get('http://localhost:44822/init').json().get('bot_id')
game_map = get('http://localhost:44822/game/{}'.format(bot_id)).json().get('map')


def compute_orientation_price(start_orientation, wanted_orientation):
    length = abs(wanted_orientation - start_orientation)
    assert 0 <= length <= 3
    return length if length < 3 else 1


def get_orientation_position_to_position(from_position, to_position):
    if from_position[0] == to_position[0] and from_position[1] == to_position[1] + 1:
        return NORTH
    elif from_position[0] == to_position[0] and from_position[1] == to_position[1] - 1:
        return SOUTH
    elif from_position[0] == to_position[0] + 1 and from_position[1] == to_position[1]:
        return WEST
    elif from_position[0] == to_position[0] - 1 and from_position[1] == to_position[1]:
        return EAST
    else:
        assert False


def get_available_closest_positions(position):
    available_closest_positions = []
    for x, y in (
            (position[0], position[1] + 1),
            (position[0], position[1] - 1),
            (position[0] + 1, position[1]),
            (position[0] - 1, position[1])
    ):
        if 0 <= x < MAP_HEIGHT and 0 <= y < MAP_WIDTH:
            available_closest_positions.append((x, y))

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
        assert all(map(lambda x: x >= 0, position))
        return super().__getitem__(position[0])[position[1]]

def get_path(game_map, start_bot_position, start_orientation):
    treasures = get_field_occurrences(TREASURE)

    def rate_game_map(game_map, position=start_bot_position, last_direction=start_orientation):
        price = 0

        data = [(price, position, last_direction)]

        while data:
            price, position, last_direction = data.pop()
            # shuffle(available_positions)
            field = game_map[position]
            if field.get('price', 10 ** 9) > price:
                field.update(dict(price=price))

            available_positions = get_available_closest_positions(position)
            for new_position in available_positions:
                new_field = game_map[new_position]
                assert isinstance(new_field, dict)
                if new_field.get('price', 10 ** 9) > price:
                    new_direction = get_orientation_position_to_position(position, new_position)
                    orientation_price = compute_orientation_price(last_direction, new_direction)

                    new_price = price + 1 + orientation_price

                    data.append((new_price, new_position, new_direction))

        return game_map

    rate_game_map(game_map, start_bot_position, start_orientation)
    return game_map


for direction in (WEST, SOUTH, EAST, NORTH):
    rated_map = get_path(Map(deepcopy(game_map)), (7, 5), direction)
    pprint(list(list(field.get('price') for field in row) for row in rated_map))
    print()

