import time
from minesweeper import MineSweeper

def main():
    game = MineSweeper(9, 9, 10)
    game.dig(4, 4)
    game.render()
    time.sleep(1)
    game.flag(0, 0)
    game.render()
    time.sleep(1)


if __name__ == "__main__":
    main()