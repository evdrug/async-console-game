import asyncio
import curses
import time
from collections import namedtuple
from itertools import cycle
from random import choice, randint

from curses_tools import draw_frame, read_controls, get_frame_size

TIC_TIMEOUT = 0.1
COUNT_STARS = 100
SYMBOL_STARS = '+*.:'
PADDING_CANVAS = 2
MIN_ROWS = 1
MIN_COLUMNS = 1
PATH_FRAMES = 'frames'

Rows = namedtuple('Rows', ['min', 'max'])
Columns = namedtuple('Columns', ['min', 'max'])
PlayCanvas = namedtuple('PlayCanvas', ['rows', 'columns'])


async def sleep(delay_tic=1):
    for _ in range(delay_tic):
        await asyncio.sleep(0)


async def animate_spaceship(canvas, row, column):
    row = round(row)
    column = round(column)
    for item in cycle([frame1, frame1, frame2, frame2]):
        rows_direction, columns_direction, space_pressed = read_controls(
            canvas)
        frame_rows, frame_columns = get_frame_size(item)
        if rows_direction or columns_direction:
            row += rows_direction
            column += columns_direction
            play_canvas = get_play_canvas(canvas)
            if play_canvas.rows.min > row:
                row = play_canvas.rows.min - 1
            if play_canvas.rows.max - frame_rows < row:
                row = play_canvas.rows.max - frame_rows

            if play_canvas.columns.min > column - round(frame_columns / 2):
                column = play_canvas.columns.min + round(frame_columns / 2)
            if play_canvas.columns.max - round(frame_columns / 2) < column:
                column = play_canvas.columns.max - round(frame_columns / 2)

        draw_frame(canvas, row + 1, (column - round(frame_columns / 2)), item)
        await sleep()
        draw_frame(canvas, row + 1, (column - round(frame_columns / 2)), item,
                   negative=True)


async def fire(canvas, start_row, start_column, rows_speed=-0.3,
               columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await sleep()
    canvas.addstr(round(row), round(column), 'O')
    await sleep()
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - PADDING_CANVAS, columns + PADDING_CANVAS

    curses.beep()

    while MIN_ROWS < row < max_row and MIN_COLUMNS < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await sleep()
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def blink(canvas, row, column, symbol='*'):
    step = randint(0, 3)
    while True:
        if step == 0:
            canvas.addstr(row, column, symbol, curses.A_DIM)
            await sleep(20)
            step = 1

        if step == 1:
            canvas.addstr(row, column, symbol)
            await sleep(3)
            step = 2

        if step == 2:
            canvas.addstr(row, column, symbol, curses.A_BOLD)
            await sleep(5)
            step = 3

        if step == 3:
            canvas.addstr(row, column, symbol)
            await sleep(3)
            step = 0


def get_play_canvas(canvas):
    max_rows_canvas, max_columns_canvas = canvas.getmaxyx()
    max_rows = max_rows_canvas - PADDING_CANVAS
    max_columns = max_columns_canvas - PADDING_CANVAS
    return PlayCanvas(Rows(MIN_ROWS, max_rows),
                      Columns(MIN_COLUMNS, max_columns))


def draw(canvas):
    curses.curs_set(False)
    canvas.border()
    canvas.nodelay(True)

    play_canvas = get_play_canvas(canvas)
    center = play_canvas.rows.max / 2, play_canvas.columns.max / 2

    coroutines = [blink(canvas, randint(*play_canvas.rows),
                        randint(*play_canvas.columns),
                        symbol=choice(SYMBOL_STARS)) for _ in
                  range(COUNT_STARS)]
    coroutines.append(fire(canvas, *center))
    coroutines.append(animate_spaceship(canvas, *center))

    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        if len(coroutines) == 0:
            break
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


if __name__ == '__main__':
    with open(f"{PATH_FRAMES}/rocket_frame_1.txt", "r") as rocket_frame_1, \
            open(f"{PATH_FRAMES}/rocket_frame_2.txt", "r") as rocket_frame_2:
        frame1 = rocket_frame_1.read()
        frame2 = rocket_frame_2.read()

    curses.update_lines_cols()
    curses.wrapper(draw)
