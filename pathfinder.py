from bisect import insort

from requests import post, get


EMPTY = 0
TREASURE = 1
BOT = 2
BLOCK = 3
LASER_BATTERY_BOT = 4

NORTH = 0
EAST = 1
SOUTH = 2
WEST = 3

MAP_HEIGHT = 50
MAP_WIDTH = 50

post('http://localhost:44822/admin',
     dict(
         map_height=MAP_HEIGHT,
         map_width=MAP_WIDTH,
         bots=1,
         treasures=1,
         blocks=10,
         maze_game=True,
         battery_game=True,
         # laser_game=True
     ))


class Map(tuple):
    def __getitem__(self, position) -> dict:
        assert hasattr(position, '__iter__') and len(position) == 2
        assert all(map(lambda x: x >= 0, position))
        return super().__getitem__(position[0])[position[1]]


def compute_orientation_price(start_orientation: int, wanted_orientation: int) -> int:
    """
    Returns price o rotating bot from start orientation to wanted_orientation.
    :param start_orientation: Starting orientation of rotating.
    :param wanted_orientation: Ending orientation of rotating.
    :return: price of rotating
    """
    length = abs(wanted_orientation - start_orientation)
    assert 0 <= length <= 3
    return length if length < 3 else 1


def get_orientation_position_to_position(from_position: tuple, to_position: tuple) -> int:
    """
    From given positions returns oriented orientation.
    :param from_position: Starting position.
    :param to_position: Ending position.
    :return:
    """
    if from_position[0] == to_position[0] and from_position[1] == to_position[1] + 1:
        return NORTH
    elif from_position[0] == to_position[0] and from_position[1] == to_position[1] - 1:
        return SOUTH
    elif from_position[0] == to_position[0] + 1 and from_position[1] == to_position[1]:
        return WEST
    elif from_position[0] == to_position[0] - 1 and from_position[1] == to_position[1]:
        return EAST


def get_available_closest_positions(position: tuple) -> list:
    """
    Get all possible positions around the given position.
    :param position:
    :return:
    """
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


def get_field_occurrences(field_type: int, game_map: Map, **other_conditions: dict) -> list:
    """
    Returns all occurrences of field_type in given map.
    If is other_conditions filled, returns only field, which includes all items from other_conditions.
    :param field_type: Type of field
    :param game_map: Game Map
    :param other_conditions: Other conditions to filter
    :return: Tuple of positions
    """
    found = []
    for x, column in enumerate(game_map):
        for y, field in enumerate(column):
            if field.get('field') == field_type:
                found.append((x, y))
    if not other_conditions:
        return found

    found_with_conditions = []
    for position in found:
        field = game_map[position]
        if len(other_conditions) == len(field.items() & other_conditions.items()):
            found_with_conditions.append(position)
    return found_with_conditions


def get_path(game_map: Map, start_bot_position: tuple, start_orientation: int, BATTERY_GAME: bool, LASER_GAME: bool):
    def rate_game_map(game_map, position=start_bot_position, last_direction=start_orientation):
        price = 0

        data = [(price, position, last_direction)]

        while data:
            price, position, last_direction = data.pop(0)

            field = game_map[position]

            if field.get('field') == BLOCK and not LASER_GAME:
                field.update(dict(price=-1))
                continue

            # update the price
            field.update(dict(price=price))

            available_positions = get_available_closest_positions(position)
            for new_position in available_positions:
                new_field = game_map[new_position]
                assert isinstance(new_field, dict)

                if new_field.get('field') in (LASER_BATTERY_BOT, BOT):
                    new_field.update(dict(price=-1))
                    continue

                # only if next field is cheaper
                if new_field.get('price', 100000000) > price:
                    new_direction = get_orientation_position_to_position(position, new_position)
                    orientation_price = compute_orientation_price(last_direction, new_direction)

                    new_price = sum((
                        price,  # price of before field
                        1,  # price for step
                        orientation_price,  # price of changing orientation
                        1 if BATTERY_GAME else 0,  # price of battery drain for step
                        2 + 1 if LASER_GAME and new_field.get('field') == BLOCK else 0,
                        # price of charging battery for laser + firing (only if is target BLOCK)
                    ))

                    # VERY IMPORTANT FOR EFFICIENCY - insert new data sorted,
                    # first item in tuple is price and it's sorted ASC,
                    # so while cycles process at first the data with lowest price
                    insort(data, (new_price, new_position, new_direction))

        return game_map

    rate_game_map(game_map, start_bot_position, start_orientation)

    treasure_prices = {game_map[position].get('price'): position for position in
                       get_field_occurrences(TREASURE, game_map)}

    print(sorted(treasure_prices.items()))
    return game_map


def main():
    bot_id = get('http://localhost:44822/init').json().get('bot_id')
    game = get('http://localhost:44822/game/{}'.format(bot_id)).json()
    game_map = game.get('map')

    LASER_GAME = game.get('game_info', {}).get('laser_game', False)
    BATTERY_GAME = game.get('game_info', {}).get('battery_game', False)
    game_map = Map(game_map)

    bot_fields = get_field_occurrences(LASER_BATTERY_BOT if BATTERY_GAME or LASER_GAME else BOT, game_map,
                                       your_bot=True)

    rated_map = get_path(game_map, bot_fields[0], game_map[bot_fields[0]].get('orientation'), BATTERY_GAME, LASER_GAME)


if __name__ == "__main__":
    main()



