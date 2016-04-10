import time
from bisect import insort
from functools import lru_cache
from operator import itemgetter

from requests import get, post


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


class Map(tuple):
    def __getitem__(self, position) -> dict:
        assert hasattr(position, '__iter__') and len(position) == 2
        assert all(map(lambda x: x >= 0, position))
        return super().__getitem__(position[0])[position[1]]


class MapRating:
    """
    Class for rating game.
    """
    def __init__(self, game: dict, game_map: Map):
        self._game = game
        self._game_map = game_map

        game_info = game.get('game_info', {})
        self._batteries_enabled = game_info.get('battery_game', False)
        self._lasers_enabled = game_info.get('laser_game', False)

        self._map_height, self._map_width = game_info.get('map_resolutions').get('height'), \
                                            game_info.get('map_resolutions').get('width')

        self._start_bot_position = next(iter(
            get_field_occurrences(
                FieldType.LASER_BATTERY_BOT if self._batteries_enabled or self._lasers_enabled else FieldType.BOT,
                self._game_map,
                your_bot=True)
        ))
        self._rated_map = None

    def get_rated_map(self):
        """
        Return cached rated game map.
        """
        if not self._rated_map:
            self._rated_map = self.rate_game_map(
                self._game_map,
                self._start_bot_position,
                self._game_map[self._start_bot_position].get('orientation')
            )
        return self._rated_map

    def rate_game_map(self, game_map: Map, start_position: tuple, last_direction: int):
        """
        Rate game map by price of actions:
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
            near_positions = self.get_near_positions(position)
            for new_position in near_positions:
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
                        2 + 1 if self._lasers_enabled and new_field.get('field') == FieldType.BLOCK else 0,
                        # price of charging battery for laser + firing (only if is target BLOCK)
                    ))

                    # VERY IMPORTANT FOR EFFICIENCY - insert new data sorted,
                    # first item in tuple is price and it's sorted ASC,
                    # so while cycles process at first the data with lowest price
                    insort(fields_to_process, (new_price, new_position, new_direction))

        return game_map

    def get_near_positions(self, position: tuple):
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
        ) if 0 <= x < self._map_height and 0 <= y < self._map_width)


class PathFinder():
    def __init__(self, game: dict):
        self._game = game
        self._game_map = Map(game.get('map'))
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
            # ((price, (x, y)), ...)
            near_positions = tuple(
                (game_map[pos].get('price'), pos) for pos in self._map_rating.get_near_positions(actual_position) if
                pos not in path)

            # two or more positions with same price
            prices = tuple(map(itemgetter(0), near_positions))
            if len(prices) != len(set(prices)):
                next_position = self._get_preferred_position(near_positions, self._map_rating._start_bot_position)
            else:
                _, next_position = min(near_positions)

            path.append(next_position)
            actual_position = next_position

        return tuple(reversed(path))

    @staticmethod
    def _get_preferred_position(possible_positions, to_position):
        positions = set(pos[1][0] for pos in possible_positions), set(pos[1][1] for pos in possible_positions)
        if max(positions[0]) < to_position[0]:
            x = max(positions[0])
        elif min(positions[0]) > to_position[0]:
            x = min(positions[0])
        else:
            x = to_position[0]

        if max(positions[1]) < to_position[1]:
            y = max(positions[1])
        elif min(positions[1]) > to_position[1]:
            y = min(positions[1])
        else:
            y = to_position[1]

        return x, y

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


def solve(game: dict):
    start = time.process_time()
    path_finder = PathFinder(game)
    path = path_finder.get_path()
    end = time.process_time()
    print('In {:5} ms through {:3} steps from {:8} to {:8}.'.format(int((end - start) * 1000), len(path), str(path[0]),
                                                                    str(path[-1])))

    return path


def main():
    post('http://localhost:44822/admin',
         dict(
             map_height=50,
             map_width=50,
             bots=2,
             treasures=2,
             blocks=10,
             maze_game=True,
             battery_game=True,
             laser_game=True
         ))

    bot_id = get('http://localhost:44822/init').json().get('bot_id')
    game = get('http://localhost:44822/game/{}'.format(bot_id)).json()

    solve(game)


if __name__ == "__main__":
    main()
