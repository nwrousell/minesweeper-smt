from __future__ import annotations

import random
from enum import IntEnum

import pygame

CELL_SIZE = 32
HEADER_HEIGHT = 48

_COLOR_UNREVEALED = (180, 180, 180)
_COLOR_UNREVEALED_BORDER = (140, 140, 140)
_COLOR_REVEALED = (220, 220, 220)
_COLOR_REVEALED_BORDER = (200, 200, 200)
_COLOR_MINE = (220, 50, 50)
_COLOR_FLAG = (240, 180, 30)
_COLOR_BG = (240, 240, 240)
_COLOR_HEADER_BG = (60, 60, 60)
_COLOR_HEADER_TEXT = (255, 255, 255)
_COLOR_GAME_OVER = (220, 50, 50)
_COLOR_WIN = (30, 180, 60)
_COLOR_HIGHLIGHT_TOP = (210, 210, 210)
_COLOR_HIGHLIGHT_BOT = (130, 130, 130)

_NUMBER_COLORS: dict[int, tuple[int, int, int]] = {
    1: (25, 118, 210),
    2: (56, 142, 60),
    3: (211, 47, 47),
    4: (123, 31, 162),
    5: (255, 143, 0),
    6: (0, 151, 167),
    7: (66, 66, 66),
    8: (158, 158, 158),
}


class CellValue(IntEnum):
    MINE = -1


class MineSweeper:
    """Minesweeper with an integrated pygame display.

    The class owns all game state *and* the pygame window. Use it
    programmatically from any script:

        game = MineSweeper(16, 16, 40)
        game.dig(8, 8)
        game.render()          # redraws & pumps OS events
        print(game.get_cell(8, 8))
        game.close()
    """

    def __init__(self, rows: int = 16, cols: int = 16, num_mines: int = 40) -> None:
        self.rows = rows
        self.cols = cols
        self.num_mines = min(num_mines, rows * cols - 9)

        self._board: list[list[int]] = [[0] * cols for _ in range(rows)]
        self._revealed: list[list[bool]] = [[False] * cols for _ in range(rows)]
        self._flagged: list[list[bool]] = [[False] * cols for _ in range(rows)]
        self._game_over = False
        self._won = False
        self._first_dig = True
        self._revealed_count = 0

        pygame.init()
        self._width = cols * CELL_SIZE
        self._height = rows * CELL_SIZE + HEADER_HEIGHT
        self._screen = pygame.display.set_mode((self._width, self._height))
        pygame.display.set_caption("Minesweeper")
        self._font = pygame.font.SysFont("consolas", 18, bold=True)
        self._clock = pygame.time.Clock()

        self.render()

    # ------------------------------------------------------------------
    # Public interface — game actions
    # ------------------------------------------------------------------

    def dig(self, row: int, col: int) -> bool:
        """Reveal a cell. Returns True if safe, False if a mine was hit."""
        if self._game_over or self._won:
            return True
        if not self._in_bounds(row, col):
            return True
        if self._revealed[row][col] or self._flagged[row][col]:
            return True

        if self._first_dig:
            self._place_mines(row, col)
            self._first_dig = False

        if self._board[row][col] == CellValue.MINE:
            self._game_over = True
            self._reveal_all_mines()
            return False

        self._flood_fill(row, col)
        self._check_win()
        return True

    def flag(self, row: int, col: int) -> None:
        """Toggle a flag on an unrevealed cell."""
        if self._game_over or self._won:
            return
        if not self._in_bounds(row, col):
            return
        if self._revealed[row][col]:
            return
        self._flagged[row][col] = not self._flagged[row][col]

    # ------------------------------------------------------------------
    # Public interface — queries
    # ------------------------------------------------------------------

    def get_cell(self, row: int, col: int) -> int | None:
        """Return the visible value of a cell: 0-8 if revealed, None otherwise."""
        if not self._in_bounds(row, col):
            return None
        if not self._revealed[row][col]:
            return None
        return self._board[row][col]

    def is_revealed(self, row: int, col: int) -> bool:
        return self._in_bounds(row, col) and self._revealed[row][col]

    def is_flagged(self, row: int, col: int) -> bool:
        return self._in_bounds(row, col) and self._flagged[row][col]

    @property
    def game_over(self) -> bool:
        return self._game_over

    @property
    def won(self) -> bool:
        return self._won

    @property
    def mines_remaining(self) -> int:
        flag_count = sum(
            self._flagged[r][c] for r in range(self.rows) for c in range(self.cols)
        )
        return self.num_mines - flag_count

    # ------------------------------------------------------------------
    # Public interface — display & lifecycle
    # ------------------------------------------------------------------

    def render(self) -> None:
        """Redraw the board and pump OS/pygame events so the window stays responsive."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
                return
        self._screen.fill(_COLOR_BG)
        self._draw_header()
        self._draw_board()
        pygame.display.flip()
        self._clock.tick(60)

    def reset(self) -> None:
        """Reset the board for a new game with the same dimensions."""
        self._board = [[0] * self.cols for _ in range(self.rows)]
        self._revealed = [[False] * self.cols for _ in range(self.rows)]
        self._flagged = [[False] * self.cols for _ in range(self.rows)]
        self._game_over = False
        self._won = False
        self._first_dig = True
        self._revealed_count = 0
        self.render()

    def close(self) -> None:
        """Shut down the pygame display."""
        pygame.quit()

    # ------------------------------------------------------------------
    # Internal — mine placement & game logic
    # ------------------------------------------------------------------

    def _in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols

    def _neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        result = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if self._in_bounds(nr, nc):
                    result.append((nr, nc))
        return result

    def _place_mines(self, safe_row: int, safe_col: int) -> None:
        safe_zone = {(safe_row, safe_col)} | set(self._neighbors(safe_row, safe_col))
        candidates = [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if (r, c) not in safe_zone
        ]
        mine_positions = random.sample(candidates, self.num_mines)
        for r, c in mine_positions:
            self._board[r][c] = CellValue.MINE
        for r in range(self.rows):
            for c in range(self.cols):
                if self._board[r][c] == CellValue.MINE:
                    continue
                self._board[r][c] = sum(
                    1
                    for nr, nc in self._neighbors(r, c)
                    if self._board[nr][nc] == CellValue.MINE
                )

    def _flood_fill(self, row: int, col: int) -> None:
        stack = [(row, col)]
        while stack:
            r, c = stack.pop()
            if self._revealed[r][c]:
                continue
            self._revealed[r][c] = True
            self._revealed_count += 1
            if self._board[r][c] == 0:
                for nr, nc in self._neighbors(r, c):
                    if not self._revealed[nr][nc] and not self._flagged[nr][nc]:
                        stack.append((nr, nc))

    def _reveal_all_mines(self) -> None:
        for r in range(self.rows):
            for c in range(self.cols):
                if self._board[r][c] == CellValue.MINE:
                    self._revealed[r][c] = True

    def _check_win(self) -> None:
        if self._revealed_count == self.rows * self.cols - self.num_mines:
            self._won = True

    # ------------------------------------------------------------------
    # Internal — rendering
    # ------------------------------------------------------------------

    def _draw_board(self) -> None:
        for r in range(self.rows):
            for c in range(self.cols):
                x = c * CELL_SIZE
                y = r * CELL_SIZE + HEADER_HEIGHT
                rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)

                if self._revealed[r][c]:
                    pygame.draw.rect(self._screen, _COLOR_REVEALED, rect)
                    pygame.draw.rect(self._screen, _COLOR_REVEALED_BORDER, rect, 1)

                    val = self._board[r][c]
                    if val == CellValue.MINE:
                        center = (x + CELL_SIZE // 2, y + CELL_SIZE // 2)
                        pygame.draw.circle(self._screen, _COLOR_MINE, center, CELL_SIZE // 4)
                    elif val > 0:
                        color = _NUMBER_COLORS.get(val, (0, 0, 0))
                        text_surf = self._font.render(str(val), True, color)
                        text_rect = text_surf.get_rect(center=rect.center)
                        self._screen.blit(text_surf, text_rect)
                else:
                    pygame.draw.rect(self._screen, _COLOR_UNREVEALED, rect)
                    pygame.draw.rect(self._screen, _COLOR_UNREVEALED_BORDER, rect, 1)

                    x2 = x + CELL_SIZE - 1
                    y2 = y + CELL_SIZE - 1
                    pygame.draw.line(self._screen, _COLOR_HIGHLIGHT_TOP, (x, y), (x2, y))
                    pygame.draw.line(self._screen, _COLOR_HIGHLIGHT_TOP, (x, y), (x, y2))
                    pygame.draw.line(self._screen, _COLOR_HIGHLIGHT_BOT, (x2, y), (x2, y2))
                    pygame.draw.line(self._screen, _COLOR_HIGHLIGHT_BOT, (x, y2), (x2, y2))

                    if self._flagged[r][c]:
                        cx = x + CELL_SIZE // 2
                        cy = y + CELL_SIZE // 2
                        s = CELL_SIZE // 4
                        pygame.draw.polygon(
                            self._screen,
                            _COLOR_FLAG,
                            [(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)],
                        )

    def _draw_header(self) -> None:
        header_rect = pygame.Rect(0, 0, self._width, HEADER_HEIGHT)
        pygame.draw.rect(self._screen, _COLOR_HEADER_BG, header_rect)

        mines_text = self._font.render(
            f"Mines: {self.mines_remaining}", True, _COLOR_HEADER_TEXT
        )
        self._screen.blit(
            mines_text, (12, HEADER_HEIGHT // 2 - mines_text.get_height() // 2)
        )

        if self._game_over:
            status = self._font.render("Game Over!", True, _COLOR_GAME_OVER)
        elif self._won:
            status = self._font.render("You Win!", True, _COLOR_WIN)
        else:
            status = self._font.render("Playing", True, _COLOR_HEADER_TEXT)

        self._screen.blit(
            status,
            (
                self._width - status.get_width() - 12,
                HEADER_HEIGHT // 2 - status.get_height() // 2,
            ),
        )


# ======================================================================
# Standalone interactive mode
# ======================================================================


def run(rows: int = 16, cols: int = 16, num_mines: int = 40) -> None:
    """Play interactively with mouse clicks."""
    game = MineSweeper(rows, cols, num_mines)
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                col = mx // CELL_SIZE
                row = (my - HEADER_HEIGHT) // CELL_SIZE

                if my < HEADER_HEIGHT:
                    if game.game_over or game.won:
                        game.reset()
                    continue

                if not game._in_bounds(row, col):
                    continue

                if event.button == 1:
                    if game.game_over or game.won:
                        game.reset()
                    else:
                        game.dig(row, col)
                elif event.button == 3:
                    game.flag(row, col)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    game.reset()

        game.render()

    game.close()


if __name__ == "__main__":
    run()
