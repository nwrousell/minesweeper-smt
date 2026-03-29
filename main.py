import time
import random
import fire
from minesweeper import MineSweeper
from z3 import *
from collections import deque

ACTIONS_PER_SEC = 2.0
NUM_ROWS = 20
NUM_COLS = 20
NUM_BOMBS = (NUM_ROWS * NUM_COLS) // 10

def main(seed: int | None = None, gif_path: str | None = None):
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    print(f"seed: {seed}")
    random.seed(seed)

    game = MineSweeper(NUM_ROWS, NUM_COLS, NUM_BOMBS)
    if gif_path:
        game.start_recording()
    safe, revealed = game.dig(4, 4)
    assert safe

    # set up n x n bool vars
    solver = Solver()
    is_bomb = [[Bool(f"{r}-{c}") for c in range(NUM_COLS)] for r in range(NUM_ROWS)]

    def in_bounds(r, c):
        return r >= 0 and r < NUM_ROWS and c >= 0 and c < NUM_COLS

    def neighbors(r, c):
        neighbors = []
        for offset_r in range(-1, 2):
            for offset_c in range(-1, 2):
                neighbor = (r + offset_r, c + offset_c)
                if neighbor != (r, c) and in_bounds(*neighbor):
                    neighbors.append(neighbor)
        return neighbors

    def gen_constraints_for_revealed_square(r, c, num_revealed):
        is_not_bomb_constraint = is_bomb[r][c] == False
        adjacency_constraint = PbEq([(is_bomb[nr][nc], 1) for nr, nc in neighbors(r, c)], num_revealed)
        return is_not_bomb_constraint, adjacency_constraint

    for r, c, val in revealed:
        solver.add(*gen_constraints_for_revealed_square(r, c, val))
    print("initial check: ", solver.check())

    frontier = deque(game.get_perimeter())
    while True:
        game.render()
        time.sleep(1 / ACTIONS_PER_SEC)

        if len(frontier) == 0:
            break
        while True:
            r, c = frontier.popleft()

            solver.push() # checkpoint constraints
            solver.add(is_bomb[r][c] == True)
            if solver.check() == unsat:
                safe, revealed = game.dig(r, c)
                assert safe

                solver.pop() # undo hypothetical

                for nr, nc, val in revealed:
                    solver.add(*gen_constraints_for_revealed_square(nr, nc, val))
                    for neighbor in neighbors(nr, nc):
                        if neighbor not in frontier and not game.is_revealed(*neighbor) and not game.is_flagged(*neighbor):
                            frontier.append(neighbor)

                break
            else:
                # possible for a bomb to be there
                solver.pop()

                # MUST there be one?
                solver.push()
                solver.add(is_bomb[r][c] == False)
                if solver.check() == unsat:
                    # yup - flag it!
                    game.flag(r, c)
                    game.render()
                else:
                    frontier.append((r, c)) # look at this square again later when more is known
                solver.pop() # undo hypothetical

    game.render()
    if gif_path:
        game.save_gif(gif_path)

    while not game.closed:
        game.render()


if __name__ == "__main__":
    fire.Fire(main)