from bisect import insort
from functools import lru_cache
from pprint import pprint

from requests import post, get


class FieldType():
    EMPTY = 0
    TREASURE = 1
    BOT = 2
    BLOCK = 3
    LASER_BATTERY_BOT = 4


NORTH = 0
EAST = 1
SOUTH = 2
WEST = 3

MAP_HEIGHT = 60
MAP_WIDTH = 60


class Map(tuple):
    def __getitem__(self, position) -> dict:
        assert hasattr(position, '__iter__') and len(position) == 2
        assert all(map(lambda x: x >= 0, position))
        return super().__getitem__(position[0])[position[1]]


class MapRating():
    def __init__(self, game: dict, game_map: Map):
        self._game = game
        self._game_map = game_map
        self._batteries_enabled = game.get('game_info', {}).get('battery_game', False)
        self._lasers_enabled = game.get('game_info', {}).get('laser_game', False)
        self._start_bot_position = next(iter(
            get_field_occurrences(
                FieldType.LASER_BATTERY_BOT if self._batteries_enabled or self._lasers_enabled else FieldType.BOT,
                self._game_map,
                your_bot=True)
        ))
        self._rated_map = None

    def get_rated_map(self):
        if not self._rated_map:
            self._rated_map = self.rate_game_map(
                self._game_map,
                self._start_bot_position,
                self._game_map[self._start_bot_position].get('orientation')
            )
        return self._rated_map

    def rate_game_map(self, game_map: Map, start_position: tuple, last_direction: int):
        """Rate game map by price of actions:
            step - 1 + 1 if batteries are enabled
            rotate - 1
            laser to destroy block - 2 battery levels for laser + 1 for step on destroyed block
        :param game_map: Map instance for rating
        :param start_position: started position for rating (start position of bot)
        :param last_direction: direction of bot
        :return: rated game map
        """
        price = 0
        position = start_position
        # (price of near field, position of field, last direction of bot)
        fields_to_process = [(price, position, last_direction)]

        while fields_to_process:
            price, position, last_direction = fields_to_process.pop(0)

            field = game_map[position]

            if field.get('field') == FieldType.BLOCK and not self._lasers_enabled:
                field.update(dict(price=-1))
                continue

            # update the price
            field.update(dict(price=price))

            for new_position in get_near_positions(position):
                new_field = game_map[new_position]
                assert isinstance(new_field, dict)

                if new_field.get('field') in (FieldType.LASER_BATTERY_BOT, FieldType.BOT):
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
                        1 if self._batteries_enabled else 0,  # price of battery drain for step
                        (2 + 1) if self._lasers_enabled and new_field.get('field') == FieldType.BLOCK else 0,
                        # price of charging battery for laser + firing (only if is target BLOCK)
                    ))

                    # VERY IMPORTANT FOR EFFICIENCY - insert new data sorted,
                    # first item in tuple is price and it's sorted ASC,
                    # so while cycles process at first the data with lowest price
                    insort(fields_to_process, (new_price, new_position, new_direction))

        return game_map


class PathFinder():
    def __init__(self, game: dict):
        self._game = game
        self._game_map = Map(game.get('map'))
        # self._game_map = Map(([{'price': 73, 'field': 0}, {'price': 71, 'field': 0}, {'price': 69, 'field': 0}, {'price': 67, 'field': 0}, {'price': 65, 'field': 0}, {'price': 63, 'field': 0}, {'price': 61, 'field': 0}, {'price': 59, 'field': 0}, {'price': 57, 'field': 0}, {'price': 55, 'field': 0}, {'price': 53, 'field': 0}, {'price': 51, 'field': 0}, {'price': 49, 'field': 0}, {'price': 47, 'field': 3}, {'price': 42, 'field': 0}, {'price': 40, 'field': 0}, {'price': 37, 'field': 0}, {'price': 41, 'field': 0}, {'price': 37, 'field': 0}, {'price': 41, 'field': 0}], [{'price': 83, 'field': 3}, {'price': 81, 'field': 3}, {'price': 79, 'field': 3}, {'price': 78, 'field': 3}, {'price': 75, 'field': 3}, {'price': 73, 'field': 3}, {'price': 71, 'field': 3}, {'price': 69, 'field': 3}, {'price': 67, 'field': 3}, {'price': 66, 'field': 3}, {'price': 58, 'field': 0}, {'price': 59, 'field': 3}, {'price': 52, 'field': 0}, {'price': 53, 'field': 3}, {'price': 45, 'field': 0}, {'price': 46, 'field': 3}, {'price': 35, 'field': 0}, {'price': 42, 'field': 3}, {'price': 35, 'field': 3}, {'price': 41, 'field': 3}], [{'price': 77, 'field': 0}, {'price': 75, 'field': 0}, {'price': 72, 'field': 0}, {'price': 78, 'field': 3}, {'price': 67, 'field': 0}, {'price': 65, 'field': 0}, {'price': 63, 'field': 0}, {'price': 61, 'field': 0}, {'price': 58, 'field': 0}, {'price': 64, 'field': 3}, {'price': 56, 'field': 0}, {'price': 57, 'field': 3}, {'price': 49, 'field': 0}, {'price': 50, 'field': 3}, {'price': 42, 'field': 0}, {'price': 43, 'field': 3}, {'price': 33, 'field': 0}, {'price': 36, 'field': 0}, {'price': 30, 'field': 0}, {'price': 34, 'field': 0}], [{'price': 83, 'field': 3}, {'price': 81, 'field': 3}, {'price': 70, 'field': 0}, {'price': 78, 'field': 3}, {'price': 70, 'field': 0}, {'price': 71, 'field': 3}, {'price': 60, 'field': 0}, {'price': 67, 'field': 3}, {'price': 56, 'field': 0}, {'price': 62, 'field': 3}, {'price': 53, 'field': 0}, {'price': 55, 'field': 3}, {'price': 47, 'field': 0}, {'price': 48, 'field': 3}, {'price': 40, 'field': 0}, {'price': 41, 'field': 3}, {'price': 31, 'field': 0}, {'price': 39, 'field': 3}, {'price': 28, 'field': 0}, {'price': 32, 'field': 0}], [{'price': 73, 'field': 0}, {'price': 71, 'field': 0}, {'price': 68, 'field': 0}, {'price': 74, 'field': 3}, {'price': 67, 'field': 0}, {'price': 68, 'field': 3}, {'price': 58, 'field': 0}, {'price': 64, 'field': 3}, {'price': 54, 'field': 0}, {'price': 60, 'field': 3}, {'price': 51, 'field': 0}, {'price': 49, 'field': 3}, {'price': 44, 'field': 0}, {'price': 46, 'field': 3}, {'price': 38, 'field': 0}, {'price': 39, 'field': 3}, {'price': 29, 'field': 0}, {'price': 36, 'field': 3}, {'price': 26, 'field': 0}, {'price': 30, 'field': 0}], [{'price': 76, 'field': 0}, {'price': 77, 'field': 3}, {'price': 66, 'field': 0}, {'price': 77, 'field': 3}, {'price': 67, 'field': 3}, {'price': 66, 'field': 3}, {'price': 56, 'field': 0}, {'price': 62, 'field': 3}, {'price': 52, 'field': 0}, {'price': 62, 'field': 3}, {'price': 62, 'field': 1}, {'price': 55, 'field': 3}, {'price': 50, 'field': 3}, {'price': 44, 'field': 3}, {'price': 36, 'field': 0}, {'price': 37, 'field': 3}, {'price': 27, 'field': 0}, {'price': 34, 'field': 3}, {'price': 24, 'field': 0}, {'price': 28, 'field': 0}], [{'price': 76, 'field': 1}, {'price': 74, 'field': 3}, {'price': 64, 'field': 0}, {'price': 70, 'field': 3}, {'price': 60, 'field': 0}, {'price': 66, 'field': 3}, {'price': 54, 'field': 0}, {'price': 60, 'field': 3}, {'price': 50, 'field': 0}, {'price': 56, 'field': 3}, {'price': 48, 'field': 0}, {'price': 49, 'field': 3}, {'price': 41, 'field': 0}, {'price': 42, 'field': 3}, {'price': 34, 'field': 0}, {'price': 35, 'field': 3}, {'price': 25, 'field': 0}, {'price': 32, 'field': 3}, {'price': 22, 'field': 0}, {'price': 26, 'field': 0}], [{'price': 70, 'field': 0}, {'price': 70, 'field': 3}, {'price': 62, 'field': 0}, {'price': 68, 'field': 3}, {'price': 58, 'field': 0}, {'price': 64, 'field': 3}, {'price': 52, 'field': 0}, {'price': 58, 'field': 3}, {'price': 48, 'field': 0}, {'price': 54, 'field': 3}, {'price': 45, 'field': 0}, {'price': 45, 'field': 3}, {'price': 38, 'field': 0}, {'price': 38, 'field': 3}, {'price': 31, 'field': 0}, {'price': 31, 'field': 3}, {'price': 23, 'field': 0}, {'price': 29, 'field': 3}, {'price': 20, 'field': 3}, {'price': 26, 'field': 3}], [{'price': 67, 'field': 0}, {'price': 68, 'field': 3}, {'price': 59, 'field': 0}, {'price': 57, 'field': 0}, {'price': 55, 'field': 0}, {'price': 53, 'field': 0}, {'price': 50, 'field': 0}, {'price': 56, 'field': 3}, {'price': 46, 'field': 0}, {'price': 43, 'field': 0}, {'price': 41, 'field': 0}, {'price': 39, 'field': 3}, {'price': 34, 'field': 0}, {'price': 32, 'field': 3}, {'price': 27, 'field': 0}, {'price': 25, 'field': 3}, {'price': 20, 'field': 0}, {'price': 18, 'field': 0}, {'price': 15, 'field': 0}, {'price': 19, 'field': 0}], [{'price': 69, 'field': 3}, {'price': 67, 'field': 3}, {'price': 65, 'field': 3}, {'price': 63, 'field': 3}, {'price': 61, 'field': 3}, {'price': 59, 'field': 3}, {'price': 48, 'field': 0}, {'price': 56, 'field': 3}, {'price': 44, 'field': 0}, {'price': 50, 'field': 3}, {'price': 47, 'field': 3}, {'price': 45, 'field': 3}, {'price': 37, 'field': 0}, {'price': 38, 'field': 3}, {'price': 30, 'field': 0}, {'price': 31, 'field': 3}, {'price': 23, 'field': 0}, {'price': 24, 'field': 3}, {'price': 13, 'field': 0}, {'price': 17, 'field': 0}], [{'price': 59, 'field': 0}, {'price': 57, 'field': 0}, {'price': 55, 'field': 0}, {'price': 53, 'field': 0}, {'price': 51, 'field': 0}, {'price': 49, 'field': 0}, {'price': 46, 'field': 0}, {'price': 52, 'field': 3}, {'price': 41, 'field': 0}, {'price': 39, 'field': 0}, {'price': 37, 'field': 0}, {'price': 37, 'field': 0}, {'price': 34, 'field': 0}, {'price': 35, 'field': 3}, {'price': 27, 'field': 0}, {'price': 28, 'field': 3}, {'price': 20, 'field': 0}, {'price': 21, 'field': 3}, {'price': 11, 'field': 0}, {'price': 15, 'field': 0}], [{'price': 62, 'field': 0}, {'price': 68, 'field': 3}, {'price': 60, 'field': 0}, {'price': 61, 'field': 3}, {'price': 54, 'field': 0}, {'price': 55, 'field': 3}, {'price': 44, 'field': 0}, {'price': 53, 'field': 3}, {'price': 47, 'field': 3}, {'price': 45, 'field': 3}, {'price': 43, 'field': 3}, {'price': 41, 'field': 3}, {'price': 32, 'field': 0}, {'price': 33, 'field': 3}, {'price': 25, 'field': 0}, {'price': 26, 'field': 3}, {'price': 18, 'field': 0}, {'price': 19, 'field': 3}, {'price': 9, 'field': 0}, {'price': 13, 'field': 0}], [{'price': 58, 'field': 0}, {'price': 66, 'field': 3}, {'price': 58, 'field': 0}, {'price': 59, 'field': 3}, {'price': 51, 'field': 0}, {'price': 52, 'field': 3}, {'price': 42, 'field': 0}, {'price': 48, 'field': 3}, {'price': 39, 'field': 0}, {'price': 37, 'field': 0}, {'price': 35, 'field': 0}, {'price': 32, 'field': 0}, {'price': 29, 'field': 0}, {'price': 31, 'field': 3}, {'price': 23, 'field': 0}, {'price': 24, 'field': 3}, {'price': 16, 'field': 0}, {'price': 17, 'field': 3}, {'price': 7, 'field': 0}, {'price': 11, 'field': 0}], [{'price': 56, 'field': 0}, {'price': 63, 'field': 3}, {'price': 55, 'field': 0}, {'price': 55, 'field': 3}, {'price': 48, 'field': 0}, {'price': 48, 'field': 3}, {'price': 40, 'field': 0}, {'price': 46, 'field': 3}, {'price': 40, 'field': 3}, {'price': 38, 'field': 3}, {'price': 36, 'field': 3}, {'price': 30, 'field': 3}, {'name': 'Terry', 'battery_level': 10, 'orientation': 0, 'field': 4, 'price': -1}, {'price': 27, 'field': 3}, {'price': 21, 'field': 0}, {'price': 22, 'field': 3}, {'price': 14, 'field': 0}, {'price': 15, 'field': 3}, {'price': 5, 'field': 0}, {'price': 9, 'field': 0}], [{'price': 54, 'field': 0}, {'price': 60, 'field': 3}, {'price': 51, 'field': 0}, {'price': 49, 'field': 3}, {'price': 44, 'field': 0}, {'price': 42, 'field': 3}, {'price': 37, 'field': 0}, {'price': 35, 'field': 3}, {'price': 30, 'field': 0}, {'price': 28, 'field': 0}, {'price': 26, 'field': 0}, {'price': 24, 'field': 0}, {'price': 22, 'field': 0}, {'price': 20, 'field': 0}, {'price': 20, 'field': 0}, {'price': 18, 'field': 3}, {'price': 11, 'field': 0}, {'price': 11, 'field': 3}, {'price': 3, 'field': 0}, {'price': 7, 'field': 0}], [{'price': 52, 'field': 0}, {'price': 58, 'field': 3}, {'price': 57, 'field': 3}, {'price': 55, 'field': 3}, {'price': 51, 'field': 3}, {'price': 49, 'field': 3}, {'price': 47, 'field': 3}, {'price': 41, 'field': 3}, {'name': 'Mark', 'battery_level': 10, 'orientation': 0, 'field': 4, 'price': -1}, {'price': 38, 'field': 3}, {'price': 36, 'field': 3}, {'price': 34, 'field': 3}, {'price': 32, 'field': 3}, {'price': 26, 'field': 3}, {'price': 17, 'field': 3}, {'price': 12, 'field': 3}, {'price': 7, 'field': 0}, {'price': 5, 'field': 3}, {'name': 'Michael', 'battery_level': 10, 'orientation': 0, 'field': 4, 'your_bot': True, 'price': -1}, {'price': 4, 'field': 0}], [{'price': 49, 'field': 0}, {'price': 47, 'field': 0}, {'price': 45, 'field': 0}, {'price': 43, 'field': 0}, {'price': 41, 'field': 0}, {'price': 39, 'field': 0}, {'price': 37, 'field': 0}, {'price': 35, 'field': 3}, {'price': 30, 'field': 0}, {'price': 28, 'field': 0}, {'price': 26, 'field': 0}, {'price': 24, 'field': 0}, {'price': 22, 'field': 0}, {'price': 20, 'field': 0}, {'price': 20, 'field': 0}, {'price': 18, 'field': 3}, {'price': 11, 'field': 0}, {'price': 11, 'field': 3}, {'price': 3, 'field': 0}, {'price': 7, 'field': 0}], [{'price': 52, 'field': 0}, {'price': 58, 'field': 3}, {'price': 55, 'field': 3}, {'price': 53, 'field': 3}, {'price': 51, 'field': 3}, {'price': 49, 'field': 3}, {'price': 47, 'field': 3}, {'price': 41, 'field': 3}, {'price': 33, 'field': 0}, {'price': 39, 'field': 3}, {'price': 36, 'field': 3}, {'price': 34, 'field': 3}, {'price': 32, 'field': 3}, {'price': 31, 'field': 3}, {'price': 28, 'field': 3}, {'price': 23, 'field': 3}, {'price': 14, 'field': 0}, {'price': 16, 'field': 3}, {'price': 5, 'field': 0}, {'price': 9, 'field': 0}], [{'price': 54, 'field': 0}, {'price': 51, 'field': 0}, {'price': 49, 'field': 0}, {'price': 47, 'field': 0}, {'price': 45, 'field': 0}, {'price': 43, 'field': 0}, {'price': 41, 'field': 0}, {'price': 45, 'field': 3}, {'price': 35, 'field': 0}, {'price': 32, 'field': 0}, {'price': 30, 'field': 0}, {'price': 28, 'field': 0}, {'price': 26, 'field': 0}, {'price': 24, 'field': 0}, {'price': 22, 'field': 0}, {'price': 26, 'field': 3}, {'price': 16, 'field': 0}, {'price': 17, 'field': 3}, {'price': 7, 'field': 0}, {'price': 11, 'field': 0}], [{'price': 57, 'field': 0}, {'price': 55, 'field': 0}, {'price': 53, 'field': 0}, {'price': 51, 'field': 0}, {'price': 49, 'field': 0}, {'price': 47, 'field': 0}, {'price': 44, 'field': 0}, {'price': 50, 'field': 3}, {'price': 50, 'field': 1}, {'price': 36, 'field': 0}, {'price': 34, 'field': 0}, {'price': 32, 'field': 0}, {'price': 30, 'field': 0}, {'price': 28, 'field': 0}, {'price': 25, 'field': 0}, {'price': 28, 'field': 3}, {'price': 18, 'field': 0}, {'price': 19, 'field': 3}, {'price': 9, 'field': 0}, {'price': 13, 'field': 0}]))
        self._map_rating = MapRating(game, self._game_map)
        treasures = {self._game_map[position].get('price'): position for position in
                     get_field_occurrences(FieldType.TREASURE, self._game_map)}
        _, self._target_position = min(treasures.items())

    def get_path(self):
        return self._resolve_path(
            self._map_rating.get_rated_map(),
            self._target_position
        )

    def _resolve_path(self, game_map: Map, target_position: tuple):
        target_price = game_map[target_position].get('price')
        assert isinstance(target_price, int) and target_price > 0

        actual_position = target_position

        path = [target_position]
        while actual_position != self._map_rating._start_bot_position:  # and price != target_price:
            near_positions = {game_map[pos].get('price'): pos for pos in get_near_positions(actual_position) if
                              pos not in path}
            # TODO: small bug in the code.. bugs everywhere
            if not near_positions:
                print(path)
                print(actual_position)
                pprint(list(list((x, y, field.get('price')) for y, field in enumerate(column)) for x, column in
                            enumerate(game_map)), width=200)
                exit(1)
            price, next_position = min(near_positions.items())

            path.append(next_position)
            actual_position = next_position
        return tuple(reversed(path))


post('http://localhost:44822/admin',
     dict(
         map_height=MAP_HEIGHT,
         map_width=MAP_WIDTH,
         bots=2,
         treasures=2,
         blocks=10,
         maze_game=True,
         battery_game=True,
         laser_game=True
     ))


@lru_cache(maxsize=12)
def compute_orientation_price(start_orientation: int, wanted_orientation: int) -> int:
    """
    Return price o rotating bot from start orientation to wanted_orientation.
    :param start_orientation: Starting orientation of rotating.
    :param wanted_orientation: Ending orientation of rotating.
    :return: price of rotating
    """
    length = abs(wanted_orientation - start_orientation)
    assert 0 <= length <= 3
    return length if length < 3 else 1


def get_orientation_position_to_position(from_position: tuple, to_position: tuple) -> int:
    """
    From given positions return oriented orientation.
    :param from_position: Starting position.
    :param to_position: Ending position.
    :return: orientation
    """
    from_position_x, from_position_y = from_position
    to_position_x, to_position_y = to_position

    if from_position_x == to_position_x and from_position_y == to_position_y + 1:
        return NORTH
    elif from_position_x == to_position_x and from_position_y == to_position_y - 1:
        return SOUTH
    elif from_position_x == to_position_x + 1 and from_position_y == to_position_y:
        return WEST
    elif from_position_x == to_position_x - 1 and from_position_y == to_position_y:
        return EAST


def get_near_positions(position: tuple):
    """
    Get all possible positions around the given position.
    :param position:
    :return:
    """

    return ((x, y) for x, y in (
        (position[0], position[1] + 1),
        (position[0], position[1] - 1),
        (position[0] + 1, position[1]),
        (position[0] - 1, position[1])
    ) if 0 <= x < MAP_HEIGHT and 0 <= y < MAP_WIDTH)


def get_field_occurrences(field_type: int, game_map: Map, **other_conditions: dict) -> list:
    """Return all occurrences of field_type in given map.
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


import time


def solve(game: dict):
    start = time.process_time()
    path_finder = PathFinder(game)
    path = path_finder.get_path()
    end = time.process_time()
    print('In {} ms through {} steps from {} to {}.'.format(int((end - start) * 1000), len(path), path[0], path[-1]))
    return path


def main():
    bot_id = get('http://localhost:44822/init').json().get('bot_id')
    game = get('http://localhost:44822/game/{}'.format(bot_id)).json()

    solve(game)


if __name__ == "__main__":
    main()


