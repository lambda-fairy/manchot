#!/usr/bin/env python
"""
========================================================================
 Welcome to Manchot!
========================================================================

To write an AI, extend the ``AI`` class and override the following
methods:

* ``make_placement(self)``
* ``make_move(self)``

These three are optional -- you may implement these if you need them:

* ``initialize(self)``
* ``enemy_placed(self, enemy_id, position)``
* ``enemy_moved(self, enemy_id, move)``

See the class ``GreedyAI`` at the end of this file for an example.

"""

from __future__ import print_function

import __builtin__
from collections import namedtuple
from functools import partial, wraps
import sys


# Force print() to flush after every move
@wraps(__builtin__.print)
def print(*args, **kwds):
    kwds.setdefault('file', sys.stdout)
    __builtin__.print(*args, **kwds)
    kwds['file'].flush()
debug = partial(print, file=sys.stderr)


# Simulate scanf("%d") using a generator
def _int_iterator():
    while True:
        line = raw_input().strip()
        for word in line.split():
            yield int(word)
read_int = _int_iterator().next
del _int_iterator


Point = namedtuple('Point', 'y x')


Move = namedtuple('Move', 'who dest')


class Tile:
    """Represents a tile in the game."""
    def __init__(self, fish=None, broken=False):
        # The number of fish on this tile
        self.fish = fish
        # Whether it's broken or not
        self.broken = broken


class State:
    """Represents the current game state."""

    def __init__(self, tiles):
        # Matrix containing all the tiles
        self.tiles = tiles
        # List mapping penguin IDs to positions
        self.penguins = []

    def move(self, m):
        """Move a penguin."""
        self.penguins[m.who] = m.dest
        self._break(m.dest)

    def place(self, pos):
        """Place a new penguin at the specified position and return its
        index."""
        self.penguins.append(pos)
        self._break(pos)
        return len(self.penguins) - 1

    def _break(self, pos):
        self.tiles[pos.y][pos.x].broken = True

    def __repr__(self):
        return '<State tiles=%s, penguins=%s>' % (self.tiles, self.penguins)


class AIBase:
    """The base class for an AI."""

    def __init__(self, state, n_penguins, me, n_players):
        self.state = state
        self.n_penguins = n_penguins
        self.me = me
        self.n_players = n_players
        self.my_penguins = []
        self.initialize()

    def initialize(self):
        """Do any initialization required for the AI."""
        pass

    def enemy_placed(self, enemy, pos):
        """Called when the opponent places a penguin."""
        pass

    def enemy_moved(self, enemy, m):
        """Called when the opponent moves a penguin."""
        pass

    def make_placement(self):
        """Return the position of the next penguin to place."""
        raise NotImplementedError('make_placement')

    def make_move(self):
        """Return the next move to make."""
        raise NotImplementedError('make_move')

    ### Internal API

    def _enemy_placed(self, enemy, pos):
        debug('Got enemy penguin at (%s, %s)' % pos)
        self.state.place(pos)
        self.enemy_placed(enemy, pos)

    def _enemy_moved(self, enemy, m):
        debug('Enemy penguin %s moved to (%s, %s)' % (
                m.who, m.dest.y, m.dest.x))
        self.state.move(m)
        self.enemy_moved(enemy, m)

    def _make_placement(self):
        pos = self.make_placement()
        debug('Placing penguin at (%s, %s)' % pos)
        self.my_penguins.append(self.state.place(pos))
        return pos

    def _make_move(self):
        m = self.make_move()
        debug('Moving penguin %s to (%s, %s)' % (
                m.who, m.dest.y, m.dest.x))
        self.state.move(m)
        return m


class Strategy:
    # Used by the greedy AI. This tends to make the penguin jump around,
    # making it harder to trap.
    DEFAULT = [
            (-1,  0), # Up
            ( 1,  0), # Down
            ( 0, -1), # Left
            ( 0,  1), # Right
            (-1, -1), # Diagonal up
            ( 1,  1), # Diagonal down
            ]

    # Used by the basic AI. This order is more "conservative", and is
    # better at covering the whole board.
    COMPLETE = [
            (-1,  0), # Up
            ( 0,  1), # Right
            ( 1,  1), # Diagonal down
            ( 1,  0), # Down
            ( 0, -1), # Left
            (-1, -1), # Diagonal up
            ]


class AIUtils:
    """A mixin with various helpers for writing an AI."""

    def iterate_penguins(self):
        """Yield a (penguin_id, position) pair for each penguin owned by
        the player."""
        for penguin in self.my_penguins:
            start = self.state.penguins[penguin]
            yield penguin, start

    def at(self, pos):
        """Return the Tile at the specified position."""
        return self.state.tiles[pos.y][pos.x]

    def iterate_tiles(self):
        """Yield a (position, tile) pair for each tile on the board."""
        for y, row in enumerate(self.state.tiles):
            for x, tile in enumerate(row):
                yield Point(y, x), tile

    def tiles_from(self, start, strategy=Strategy.DEFAULT):
        """Yield all the positions that a penguin can reach from the
        specified point."""
        for delta in strategy:
            for pos in project_ray(start, delta):
                if (not in_board(pos, self.state.tiles) or
                        self.at(pos).broken):
                    break
                else:
                    yield pos, self.at(pos)


class AI(AIBase, AIUtils):
    """A shortcut for inheriting from both AIBase and AIUtils. Your own
    AI should extend this class."""
    pass


def run(ai_cls):
    width, height, n_penguins, me, n_players = \
            read_int(), read_int(), read_int(), read_int(), read_int()

    state = State([
        [Tile() for i in range(width)]
        for i in range(height)])

    ai = ai_cls(state, n_penguins, me, n_players)

    # Read in the initial game state
    for pos, tile in ai.iterate_tiles():
        tile.fish = read_int()
    for pos, tile in ai.iterate_tiles():
        tile.broken = bool(read_int())

    # Until all penguins are placed:
    # + Read in a penguin placement
    # + Place a penguin (output <y> <x>)
    while True:
        player = read_int()
        if player == -1:
            # End of input
            break
        elif player == me:
            # I place a penguin! Who places a penguin? I do! Oh yes I *do*!
            pos = ai._make_placement()
            print(pos.y, pos.x)
        else:
            # Enemy placed a penguin
            pos = Point(read_int(), read_int())
            ai._enemy_placed(player, pos)

    # Play the game, lol
    while True:
        player = read_int()
        if player == me:
            # Make a move
            m = ai._make_move()
            print(m.who, m.dest.y, m.dest.x)
        else:
            # Enemy made a move
            penguin, dest_y, dest_x = read_int(), read_int(), read_int()
            m = Move(penguin, Point(dest_y, dest_x))
            ai._enemy_moved(player, m)


def project_ray(start, delta):
    """Yield a stream of values obtained by repeatedly adding an offset
    to a start point."""
    current = start
    while True:
        current = Point(current[0]+delta[0], current[1]+delta[1])
        yield current


def in_board(pos, tiles):
    return 0 <= pos.y < len(tiles) and 0 <= pos.x < len(tiles[0])


class GreedyAI(AI):
    """A direct translation of the example greedy solution."""

    def make_placement(self):
        # Pick the tile with the highest number of fish
        best_fish = 0
        best_pos = None
        for pos, tile in self.iterate_tiles():
            if tile.broken:
                continue
            if tile.fish > best_fish:
                best_fish = tile.fish
                best_pos = pos
        return best_pos

    def make_move(self):
        # Make the move yielding the highest number of fish
        best_fish = 0
        best_pos = None
        best_penguin = None
        for penguin, start in self.iterate_penguins():
            for pos, tile in self.tiles_from(start):
                if tile.fish > best_fish:
                    best_fish = tile.fish
                    best_pos = pos
                    best_penguin = penguin
        return Move(best_penguin, best_pos)


if __name__ == '__main__':
    run(GreedyAI)
