# Tetris

A feature-rich Tetris game built with Python and pygame.

## Features

### 🎮 Four Game Modes
| Mode | Description |
|------|-------------|
| **Classic** | Choose start level (1–15), speed increases with level |
| **Speed Run** | Starts at high speed, intense gameplay |
| **Marathon** | Clear 150 lines to win, slow start |
| **Zen** | No game over, relax and play |

### ✨ Core Features
- **7 standard tetrominoes** — I / O / T / S / Z / J / L, each with 4 rotation states
- **Shadow preview** — semi-transparent ghost shows where piece will land
- **Next piece preview** — displayed on the side panel
- **Scoring** — 1 line: 100 / 2 lines: 300 / 3 lines: 500 / 4 lines: 800, multiplied by level
- **DAS (Delayed Auto Shift)** — hold arrow keys for auto-repeat movement
- **3 save slots** — save and load progress anytime

### 🌐 LAN Multiplayer
- **No server needed, no port forwarding required**
- Host broadcasts IP automatically; others can discover and join
- Real-time versus on the same screen
- Garbage attack: clear 2 lines → send 1, 3 lines → send 2, 4 lines → send 4
- Opponent tops out = you win

## Controls

| Action | Key |
|--------|-----|
| Move left/right | ← → |
| Rotate | ↑ |
| Soft drop | ↓ |
| Hard drop | Space |
| Pause | P / ESC |
| Save / Load | Use pause menu |
| Quit | ESC (multiple presses) |

## How to Run

### Option 1: Download exe (Recommended)
Go to [Releases](https://github.com/lldcfk-xiaohao/tetris/releases) and download `tetris.exe`. Double-click to run, no Python required.

### Option 2: Run from source
```bash
pip install pygame
python tetris.py
```

## Build exe yourself
```bash
pip install pygame pyinstaller
pyinstaller --onefile --windowed --name tetris tetris.py
# exe will be in dist/tetris.exe
```

## Tech Stack
- Python 3.8+
- pygame 2.0+

## License
MIT License

## Author
[lldcfk-xiaohao](https://github.com/lldcfk-xiaohao)
