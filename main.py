import asyncio
import curses
import os
import time
from collections import namedtuple
from itertools import cycle
from random import choice, randint

from curses_tools import draw_frame, read_controls, get_frame_size
from explosion import explode
from game_scenario import get_garbage_delay_tics, PHRASES
from obstacles import Obstacle
from physics import update_speed

TIC_TIMEOUT = 0.1
COUNT_STARS = 100
SYMBOL_STARS = '+*.:'
PADDING_CANVAS = 2
MIN_ROWS = 0
MIN_COLUMNS = 1
PATH_FRAMES = 'frames'
YEAR_START = 1957
YEAR_ENABLE_GUN = 2020

Rows = namedtuple('Rows', ['min', 'max'])
Columns = namedtuple('Columns', ['min', 'max'])
PlayCanvas = namedtuple('PlayCanvas', ['rows', 'columns'])


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


def center_frame_in_canvas(rows, columns, size_row, size_column):
    return rows / 2 - size_row / 2, columns / 2 - size_column / 2


async def run_spaceship(game_canvas, row, column, canvas):
    row = round(row)
    column = round(column)
    row_speed = column_speed = 0

    for item in cycle([frame1, frame1, frame2, frame2]):
        rows_direction, columns_direction, space_pressed = read_controls(
            canvas)

        frame_rows, frame_columns = get_frame_size(item)
        row_speed, column_speed = update_speed(row_speed, column_speed, rows_direction, columns_direction)

        row += row_speed
        column += column_speed

        play_canvas = get_play_canvas(game_canvas)
        if play_canvas.rows.min > row:
            row = play_canvas.rows.min
        if play_canvas.rows.max - frame_rows < row:
            row = play_canvas.rows.max - frame_rows

        if play_canvas.columns.min > column - round(frame_columns / 2):
            column = play_canvas.columns.min + round(frame_columns / 2)
        if play_canvas.columns.max - frame_columns < column:
            column = play_canvas.columns.max - frame_columns

        draw_frame(game_canvas, row + 1, (column - round(frame_columns / 2)), item)
        if space_pressed and year >= YEAR_ENABLE_GUN:
            coroutines.append(fire(canvas, row, column))
        for obstacle in obstacles:
            if obstacle.has_collision(row, column, frame_rows, frame_columns):
                obstacles_in_last_collisions.append(obstacle)
                draw_frame(game_canvas, row + 1, (column - round(frame_columns / 2)), item, negative=True)
                await show_gameover(game_canvas)
                return
        await sleep()
        draw_frame(game_canvas, row + 1, (column - round(frame_columns / 2)), item,
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
        for obstacle in obstacles:
            if obstacle.has_collision(row, column):
                obstacles_in_last_collisions.append(obstacle)
                canvas.addstr(round(row), round(column), ' ')
                return
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
    max_columns = max_columns_canvas

    return PlayCanvas(Rows(MIN_ROWS, max_rows),
                      Columns(MIN_COLUMNS, max_columns))


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    play_canvas = get_play_canvas(canvas)
    column = max(column, 0)
    column = min(column, play_canvas.columns.max - 1)

    row = 0
    frame_size_row, frame_size_column = get_frame_size(garbage_frame)
    center_frame_row = round(frame_size_row / 2)
    center_frame_col = round(frame_size_column / 2)
    obstacle = Obstacle(row, column, frame_size_row, frame_size_column)
    obstacles.append(obstacle)
    while row < play_canvas.rows.max:
        if obstacle in obstacles_in_last_collisions:
            obstacles.remove(obstacle)
            draw_frame(canvas, row, column, garbage_frame, negative=True)
            await explode(canvas, row+center_frame_row, column+center_frame_col)
            return

        obstacle.row = row
        draw_frame(canvas, row, column, garbage_frame)
        await sleep()
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed
    else:
        obstacles.remove(obstacle)


async def fill_orbit_with_garbage(canvas):
    _, columns = canvas.getmaxyx()
    while True:
        delay_play_garbage = get_garbage_delay_tics(year)
        if not delay_play_garbage:
            await sleep()
            continue

        random_column = randint(0, columns)
        coroutines.append(fly_garbage(canvas, column=random_column, garbage_frame=choice(trash)))
        await sleep(delay_play_garbage)


async def show_gameover(canvas):
    rows, columns = canvas.getmaxyx()
    row_center, column_center = center_frame_in_canvas(rows, columns, *get_frame_size(game_ower))
    while True:
        draw_frame(canvas, row_center, column_center, game_ower)
        await sleep()


async def show_year(canvas):
    global year
    while True:
        body = f'{year} {PHRASES.get(year, "")}'
        draw_frame(canvas, 0, 1, body)
        await sleep()
        draw_frame(canvas, 0, 1, body, negative=True)


async def next_year():
    global year
    while True:
        await sleep(15)
        year += 1


def draw(canvas):
    curses.curs_set(False)
    canvas.nodelay(True)

    play_canvas = get_play_canvas(canvas)
    game_canvas = canvas.derwin(play_canvas.rows.max, play_canvas.columns.max, 0, 0)
    game_canvas.border()

    info_canvas = canvas.derwin(1, play_canvas.columns.max, play_canvas.rows.max, 0)

    game_canvas.nodelay(True)
    info_canvas.nodelay(True)

    game_canvas.refresh()
    info_canvas.refresh()

    center = play_canvas.rows.max / 2, play_canvas.columns.max / 2

    blink_position_rows = (play_canvas.rows.min, play_canvas.rows.max - PADDING_CANVAS)
    blink_position_columns = (play_canvas.columns.min, play_canvas.columns.max - PADDING_CANVAS)
    coroutines.extend([blink(canvas, randint(*blink_position_rows),
                             randint(*blink_position_columns),
                             symbol=choice(SYMBOL_STARS)) for _ in
                       range(COUNT_STARS)])
    coroutines.append(run_spaceship(game_canvas, *center, canvas))
    coroutines.append(fill_orbit_with_garbage(game_canvas))
    coroutines.append(show_year(info_canvas))
    coroutines.append(next_year())

    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        if len(coroutines) == 0:
            break
        game_canvas.border()
        game_canvas.refresh()
        info_canvas.refresh()

        time.sleep(TIC_TIMEOUT)


def open_garbage_frames(path):
    frames = []
    for filename in os.listdir(path):
        if filename.startswith('garbage') and filename.endswith('.txt'):
            with open(os.path.join(path, filename), "r") as name:
                frames.append(name.read())
    return frames


if __name__ == '__main__':
    coroutines = []
    obstacles = []
    year = YEAR_START
    obstacles_in_last_collisions = []
    trash = open_garbage_frames(PATH_FRAMES)

    with open(f"{PATH_FRAMES}/rocket_frame_1.txt", "r") as rocket_frame_1, \
            open(f"{PATH_FRAMES}/rocket_frame_2.txt", "r") as rocket_frame_2, \
            open(f"{PATH_FRAMES}/game_ower.txt", "r") as game_ower_frame:
        frame1 = rocket_frame_1.read()
        frame2 = rocket_frame_2.read()
        game_ower = game_ower_frame.read()

    curses.update_lines_cols()
    curses.wrapper(draw)
