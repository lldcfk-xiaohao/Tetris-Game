import pygame, random, sys, json, os, socket, threading, time
from collections import deque

# ===================== 常量 =====================
COLS, ROWS = 10, 20
CELL = 30
CELL_LAN = 26
FPS = 60
LAN_TCP = 19527
LAN_UDP = 19528
SAVE_DIR = "saves"

M_CLASSIC, M_SPEED, M_MARATHON, M_ZEN = 0, 1, 2, 3
MODE_NAMES = ["Classic", "Speed Run", "Marathon", "Zen"]

# 状态
S_MENU, S_LEVEL, S_LOAD, S_LAN, S_LAN_HOST, S_LAN_JOIN = 0, 1, 2, 3, 4, 5
S_PLAY, S_LAN_PLAY, S_PAUSE, S_OVER = 6, 7, 8, 9

# 方块形状 (7种 × 4旋转)
SHAPES = [
    [[(0,1),(1,1),(2,1),(3,1)],[(2,0),(2,1),(2,2),(2,3)],
     [(0,2),(1,2),(2,2),(3,2)],[(1,0),(1,1),(1,2),(1,3)]],
    [[(1,0),(2,0),(1,1),(2,1)]]*4,
    [[(1,0),(0,1),(1,1),(2,1)],[(1,0),(1,1),(2,1),(1,2)],
     [(0,1),(1,1),(2,1),(1,2)],[(1,0),(0,1),(1,1),(1,2)]],
    [[(1,0),(2,0),(0,1),(1,1)],[(1,0),(1,1),(2,1),(2,2)],
     [(1,1),(2,1),(0,2),(1,2)],[(0,0),(0,1),(1,1),(1,2)]],
    [[(0,0),(1,0),(1,1),(2,1)],[(2,0),(1,1),(2,1),(1,2)],
     [(0,1),(1,1),(1,2),(2,2)],[(1,0),(0,1),(1,1),(0,2)]],
    [[(0,0),(0,1),(1,1),(2,1)],[(1,0),(2,0),(1,1),(1,2)],
     [(0,1),(1,1),(2,1),(2,2)],[(1,0),(1,1),(0,2),(1,2)]],
    [[(2,0),(0,1),(1,1),(2,1)],[(1,0),(1,1),(1,2),(2,2)],
     [(0,1),(1,1),(2,1),(0,2)],[(0,0),(1,0),(1,1),(1,2)]],
]

COLORS = [None,
    (0,240,240),(240,240,0),(160,0,240),(0,240,0),
    (240,0,0),(0,0,240),(240,160,0),(128,128,128)]

BG       = (20, 20, 30)
BOARD_BG = (10, 10, 20)
GRID_C   = (30, 30, 45)
WHITE    = (220, 220, 220)
GRAY     = (120, 120, 140)
GOLD     = (255, 220, 80)
DARK_GOLD= (180, 150, 40)

# ===================== 工具 =====================
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

# ===================== TetrisGame =====================
class TetrisGame:
    def __init__(self, mode=0, start_level=0):
        self.mode = mode
        self.start_level = start_level
        self.last_cleared = 0
        self.reset()

    def reset(self):
        self.board = [[0]*COLS for _ in range(ROWS)]
        self.score = self.lines = 0
        self.level = self.start_level
        self.over = self.won = False
        self.next = random.randint(0, 6)
        self.tick = 0
        self.last_cleared = 0
        self._spawn()

    def _speed(self):
        if self.mode == M_SPEED:    return max(2, 16 - self.level * 2)
        if self.mode == M_MARATHON: return max(3, 28 - self.level * 2)
        if self.mode == M_ZEN:      return max(12, 50 - self.level * 2)
        return max(3, 30 - self.level * 3)

    def _spawn(self):
        self.type, self.next = self.next, random.randint(0, 6)
        self.rot = 0
        self.x = COLS // 2 - 2
        self.y = -1
        if self.mode != M_ZEN:
            if self._collide(self.type, self.rot, self.x, self.y):
                self.y = -2
                if self._collide(self.type, self.rot, self.x, self.y):
                    self.over = True

    def _cells(self, t, r, ox, oy):
        return [(dx+ox, dy+oy) for dx, dy in SHAPES[t][r]]

    def _collide(self, t, r, ox, oy):
        for x, y in self._cells(t, r, ox, oy):
            if x < 0 or x >= COLS or y >= ROWS: return True
            if y >= 0 and self.board[y][x]: return True
        return False

    def _lock(self):
        for x, y in self._cells(self.type, self.rot, self.x, self.y):
            if 0 <= y < ROWS and 0 <= x < COLS:
                self.board[y][x] = self.type + 1
        if self.mode != M_ZEN and (any(self.board[0]) or any(self.board[1])):
            self.over = True; return
        self._clear()
        self._spawn()

    def _clear(self):
        cl = 0; y = ROWS - 1
        while y >= 0:
            if all(self.board[y]):
                cl += 1; del self.board[y]; self.board.insert(0, [0]*COLS)
            else: y -= 1
        if cl:
            self.score += [0,100,300,500,800][cl] * (self.level + 1)
            self.lines += cl
            self.level = self.start_level + self.lines // 10
            if self.mode == M_MARATHON and self.lines >= 150:
                self.won = True
        self.last_cleared = cl

    def shadow_y(self):
        sy = self.y
        while not self._collide(self.type, self.rot, self.x, sy+1): sy += 1
        return sy

    def move(self, dx):
        if not self._collide(self.type, self.rot, self.x+dx, self.y): self.x += dx

    def rotate(self):
        nr = (self.rot+1) % 4
        if not self._collide(self.type, nr, self.x, self.y): self.rot = nr

    def soft_drop(self):
        if not self._collide(self.type, self.rot, self.x, self.y+1):
            self.y += 1; self.score += 1

    def hard_drop(self):
        dy = self.shadow_y()
        self.score += (dy - self.y) * 2; self.y = dy; self._lock()

    def add_garbage(self, n):
        for _ in range(n):
            if any(self.board[0]): self.over = True; return
            self.board.pop(0)
            h = random.randint(0, COLS-1)
            self.board.append([8 if x != h else 0 for x in range(COLS)])
        self.y -= n
        if self.y < -2: self.y = -2

    def update(self):
        if self.over or self.won: return
        self.tick += 1
        if self.tick >= self._speed():
            self.tick = 0
            if not self._collide(self.type, self.rot, self.x, self.y+1):
                self.y += 1
            else: self._lock()

    def state_dict(self):
        return {"board": self.board, "score": self.score, "lines": self.lines,
                "type": self.type, "rot": self.rot, "x": self.x, "y": self.y,
                "next": self.next, "over": self.over}

    def load_dict(self, d):
        for k in ("board","score","lines","type","rot","x","y","next"):
            setattr(self, k, d[k])
        self.over = d.get("over", False)
        self.level = self.start_level + self.lines // 10
        self.tick = 0; self.last_cleared = 0

# ===================== SaveManager =====================
class SaveManager:
    def __init__(self):
        self.dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), SAVE_DIR)
        os.makedirs(self.dir, exist_ok=True)

    def save(self, game, slot):
        d = {"mode": game.mode, "start_level": game.start_level,
             **game.state_dict(), "time": time.strftime("%Y-%m-%d %H:%M")}
        with open(os.path.join(self.dir, f"slot{slot}.json"), 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False)

    def load(self, slot):
        p = os.path.join(self.dir, f"slot{slot}.json")
        if not os.path.exists(p): return None
        with open(p, 'r', encoding='utf-8') as f: return json.load(f)

    def delete(self, slot):
        p = os.path.join(self.dir, f"slot{slot}.json")
        if os.path.exists(p): os.remove(p)

    def list_all(self):
        return [(i, self.load(i)) for i in range(3)]

# ===================== LANNetwork =====================
class LANNetwork:
    def __init__(self):
        self.tcp = self.conn = self._bsock = self._ssock = None
        self.is_host = self.running = self.connected = self.disconnected = False
        self._lock = threading.Lock(); self._msgs = deque()
        self.found = []; self.peer = ""

    # --- Host ---
    def host(self, name="主机"):
        self.is_host = True; self.running = True; self.connected = False
        self.disconnected = False; self.conn = None
        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp.bind(('0.0.0.0', LAN_TCP)); self.tcp.listen(1); self.tcp.settimeout(1.0)
        threading.Thread(target=self._broadcast, args=(name,), daemon=True).start()
        threading.Thread(target=self._accept, daemon=True).start()

    def _broadcast(self, name):
        self._bsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._bsock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg = f"TETRIS:{name}".encode()
        while self.running and not self.connected:
            try: self._bsock.sendto(msg, ('255.255.255.255', LAN_UDP))
            except: pass
            time.sleep(1)
        try: self._bsock.close()
        except: pass

    def _accept(self):
        while self.running and not self.connected:
            try:
                c, a = self.tcp.accept(); self.conn = c
                self.conn.settimeout(0.05); self.connected = True; self.peer = a[0]
                threading.Thread(target=self._recv, daemon=True).start()
            except socket.timeout: continue
            except: break

    # --- Client ---
    def start_scan(self):
        self.running = True; self.found = []; self.disconnected = False
        self._ssock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._ssock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._ssock.bind(('0.0.0.0', LAN_UDP)); self._ssock.settimeout(1.0)
        threading.Thread(target=self._scan, daemon=True).start()

    def _scan(self):
        lip = get_local_ip()
        while self.running:
            try:
                data, addr = self._ssock.recvfrom(1024)
                msg = data.decode()
                if msg.startswith("TETRIS:") and addr[0] != lip:
                    name = msg[7:]
                    if not any(h[0] == addr[0] for h in self.found):
                        self.found.append((addr[0], name))
            except socket.timeout: continue
            except: break

    def join(self, ip, name="客户端"):
        self.is_host = False; self.running = True; self.disconnected = False
        # 停止扫描
        self.running = False; time.sleep(0.15)
        if self._ssock:
            try: self._ssock.close()
            except: pass
        self.running = True
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((ip, LAN_TCP)); self.conn.settimeout(0.05)
        self.connected = True; self.peer = ip
        threading.Thread(target=self._recv, daemon=True).start()

    # --- Messaging ---
    def _recv(self):
        buf = ""
        while self.running and self.conn and not self.disconnected:
            try:
                data = self.conn.recv(8192)
                if not data: self.disconnected = True; break
                buf += data.decode()
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    try:
                        m = json.loads(line)
                        with self._lock: self._msgs.append(m)
                    except: pass
            except socket.timeout: continue
            except: self.disconnected = True; break

    def send(self, msg):
        if self.conn and self.connected:
            try: self.conn.sendall((json.dumps(msg, ensure_ascii=False)+'\n').encode())
            except: self.disconnected = True

    def get(self):
        with self._lock:
            ms = list(self._msgs); self._msgs.clear()
        return ms

    def stop(self):
        self.running = self.connected = False
        for s in (self.conn, self.tcp, self._bsock, self._ssock):
            if s:
                try: s.close()
                except: pass
        self.conn = self.tcp = self._bsock = self._ssock = None

# ===================== App =====================
class App:
    def __init__(self):
        pygame.init()
        self.W, self.H = 640, 640
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("Tetris")
        self.clock = pygame.time.Clock()
        self.fn  = pygame.font.SysFont("arial", 20)
        self.fnl = pygame.font.SysFont("arial", 36)
        self.fns = pygame.font.SysFont("arial", 16)
        self.fnx = pygame.font.SysFont("arial", 48)
        self.game = None
        self.state = S_MENU
        self.menu_sel = self.level_sel = self.load_sel = 0
        self.lan_sel = self.lan_join_sel = self.pause_sel = 0
        self.saves = SaveManager()
        self.net = LANNetwork()
        self.opp_board = None
        self.opp_score = self.opp_lines = 0
        self.opp_type = self.opp_rot = self.opp_x = self.opp_y = self.opp_next = 0
        self.vs_result = ""
        self.das_dir = 0; self.das_delay = 0
        self.send_tick = 0
        self.anim_t = 0
        self.err_msg = ""; self.err_time = 0

    # ---------- helpers ----------
    def _txt(self, text, x, y, color=WHITE, fn=None):
        if fn is None: fn = self.fn
        self.screen.blit(fn.render(str(text), True, color), (x, y))

    def _txtc(self, text, y, color=WHITE, fn=None):
        if fn is None: fn = self.fn
        s = fn.render(str(text), True, color)
        self.screen.blit(s, (self.W//2 - s.get_width()//2, y))

    def _draw_items(self, items, sel, y0, gap=38):
        for i, t in enumerate(items):
            c = GOLD if i == sel else WHITE
            p = "> " if i == sel else "  "
            self._txtc(p + t, y0 + i*gap, c)

    def _draw_board(self, board, ox, oy, cell):
        pygame.draw.rect(self.screen, BOARD_BG, (ox, oy, COLS*cell, ROWS*cell))
        for y in range(ROWS):
            for x in range(COLS):
                r = pygame.Rect(ox+x*cell, oy+y*cell, cell, cell)
                pygame.draw.rect(self.screen, GRID_C, r, 1)
                if board[y][x]:
                    c = COLORS[board[y][x]]
                    pygame.draw.rect(self.screen, c, (r.x+1, r.y+1, cell-2, cell-2))
                    lt = tuple(min(255, v+50) for v in c)
                    pygame.draw.rect(self.screen, lt, (r.x+1, r.y+1, cell-2, cell-2), 1)
        pygame.draw.rect(self.screen, GRAY, (ox-2, oy-2, COLS*cell+4, ROWS*cell+4), 2)

    def _draw_piece(self, game, ox, oy, cell):
        if game.over: return
        # 影子
        sy = game.shadow_y()
        if sy != game.y:
            for cx, cy in game._cells(game.type, game.rot, game.x, sy):
                if cy >= 0:
                    r = pygame.Rect(ox+cx*cell+1, oy+cy*cell+1, cell-2, cell-2)
                    sf = pygame.Surface((cell-2, cell-2), pygame.SRCALPHA)
                    c = COLORS[game.type+1]; sf.fill((*c, 50))
                    self.screen.blit(sf, r)
        # 当前方块
        for cx, cy in game._cells(game.type, game.rot, game.x, game.y):
            if cy >= 0:
                c = COLORS[game.type+1]
                r = pygame.Rect(ox+cx*cell+1, oy+cy*cell+1, cell-2, cell-2)
                pygame.draw.rect(self.screen, c, r)
                pygame.draw.rect(self.screen, tuple(min(255,v+50) for v in c), r, 1)

    def _draw_next(self, ptype, ox, oy, cell):
        for dx, dy in SHAPES[ptype][0]:
            c = COLORS[ptype+1]
            r = pygame.Rect(ox+dx*cell, oy+dy*cell, cell-2, cell-2)
            pygame.draw.rect(self.screen, c, r)
            pygame.draw.rect(self.screen, tuple(min(255,v+50) for v in c), r, 1)

    # ---------- run ----------
    def run(self):
        while True:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: self._quit()
                if ev.type == pygame.KEYDOWN: self._on_key(ev.key)
                if ev.type == pygame.KEYUP:
                    if ev.key == pygame.K_LEFT and self.das_dir == -1: self.das_dir = 0
                    if ev.key == pygame.K_RIGHT and self.das_dir == 1: self.das_dir = 0
            self._update()
            self._draw()
            pygame.display.flip()
            self.clock.tick(FPS)

    def _quit(self):
        self.net.stop(); pygame.quit(); sys.exit()

    def _go(self, state):
        self.state = state

    # ---------- key dispatch ----------
    def _on_key(self, key):
        {S_MENU: self._k_menu, S_LEVEL: self._k_level, S_LOAD: self._k_load,
         S_LAN: self._k_lan, S_LAN_HOST: self._k_lan_host, S_LAN_JOIN: self._k_lan_join,
         S_PLAY: self._k_play, S_LAN_PLAY: self._k_lan_play,
         S_PAUSE: self._k_pause, S_OVER: self._k_over,
        }.get(self.state, lambda k: None)(key)

    # ====== MENU ======
    def _k_menu(self, key):
        items = ["Classic","Speed Run","Marathon","Zen","Load Save","LAN Battle","Quit"]
        if key == pygame.K_UP:   self.menu_sel = (self.menu_sel - 1) % len(items)
        if key == pygame.K_DOWN: self.menu_sel = (self.menu_sel + 1) % len(items)
        if key == pygame.K_RETURN:
            i = self.menu_sel
            if i == 0: self._go(S_LEVEL); self.level_sel = 0
            elif i in (1,2,3): self._start_game(i, 0)
            elif i == 4: self._go(S_LOAD); self.load_sel = 0
            elif i == 5: self._go(S_LAN); self.lan_sel = 0
            elif i == 6: self._quit()
        if key == pygame.K_ESCAPE: self._quit()

    def _draw_menu(self):
        self._txtc("T E T R I S", 80, GOLD, self.fnx)
        self._draw_items(["Classic","Speed Run","Marathon","Zen",
                          "Load Save","LAN Battle","Quit"], self.menu_sel, 200)

    # ====== LEVEL SEL ======
    def _k_level(self, key):
        if key == pygame.K_LEFT:  self.level_sel = max(0, self.level_sel - 1)
        if key == pygame.K_RIGHT: self.level_sel = min(14, self.level_sel + 1)
        if key == pygame.K_RETURN: self._start_game(M_CLASSIC, self.level_sel)
        if key == pygame.K_ESCAPE: self._go(S_MENU)

    def _draw_level(self):
        self._txtc("Select Start Level", 160, WHITE, self.fnl)
        self._txtc(f"<  {self.level_sel + 1}  >", 260, GOLD, self.fnx)
        self._txtc("Left/Right adjust  Enter confirm  Esc back", 360, GRAY, self.fns)

    # ====== LOAD ======
    def _k_load(self, key):
        if key == pygame.K_UP:   self.load_sel = (self.load_sel - 1) % 3
        if key == pygame.K_DOWN: self.load_sel = (self.load_sel + 1) % 3
        if key == pygame.K_RETURN:
            d = self.saves.load(self.load_sel)
            if d: self._load_game(d)
        if key == pygame.K_DELETE:
            self.saves.delete(self.load_sel)
        if key == pygame.K_ESCAPE: self._go(S_MENU)

    def _draw_load(self):
        self._txtc("Load Save", 40, WHITE, self.fnl)
        saves = self.saves.list_all()
        for i, (slot, d) in enumerate(saves):
            y = 120 + i * 70
            c = GOLD if i == self.load_sel else WHITE
            p = "> " if i == self.load_sel else "  "
            if d:
                self._txt(f"{p}Slot {i+1}: {MODE_NAMES[d['mode']]}  Score:{d['score']}  {d.get('time','')}",
                          60, y, c)
            else:
                self._txt(f"{p}Slot {i+1}: (Empty)", 60, y, GRAY)
        self._txtc("Enter load  Del delete  Esc back", 400, GRAY, self.fns)

    # ====== LAN MENU ======
    def _k_lan(self, key):
        if key == pygame.K_UP:   self.lan_sel = (self.lan_sel - 1) % 3
        if key == pygame.K_DOWN: self.lan_sel = (self.lan_sel + 1) % 3
        if key == pygame.K_RETURN:
            if self.lan_sel == 0:
                try:
                    self.net.host("Host"); self._go(S_LAN_HOST)
                except Exception as e:
                    self.err_msg = f"Create failed: {e}"; self.err_time = 180
            elif self.lan_sel == 1:
                try:
                    self.net.start_scan(); self._go(S_LAN_JOIN); self.lan_join_sel = 0
                except Exception as e:
                    self.err_msg = f"Scan failed: {e}"; self.err_time = 180
            else: self._go(S_LAN)
        if key == pygame.K_ESCAPE: self.net.stop(); self._go(S_MENU)

    def _draw_lan(self):
        self._txtc("LAN Battle", 120, WHITE, self.fnl)
        self._txtc("Local network direct connect, no server", 170, GRAY, self.fns)
        self._draw_items(["Create Room","Search Room","Back"], self.lan_sel, 240)

    # ====== LAN HOST ======
    def _k_lan_host(self, key):
        if key == pygame.K_ESCAPE: self.net.stop(); self._go(S_LAN)

    def _draw_lan_host(self):
        self._txtc("Waiting for opponent...", 150, WHITE, self.fnl)
        self._txtc(f"Your IP: {get_local_ip()}", 220, GRAY)
        dots = "." * (1 + (self.anim_t // 30) % 3)
        self._txtc(f"Waiting{dots}", 280, WHITE)
        self._txtc("Esc cancel", 360, GRAY, self.fns)
        if self.net.connected:
            self._start_lan()

    # ====== LAN JOIN ======
    def _k_lan_join(self, key):
        n = len(self.net.found)
        if n:
            if key == pygame.K_UP:   self.lan_join_sel = (self.lan_join_sel - 1) % n
            if key == pygame.K_DOWN: self.lan_join_sel = (self.lan_join_sel + 1) % n
            if key == pygame.K_RETURN:
                ip, name = self.net.found[self.lan_join_sel]
                try:
                    self.net.join(ip); self._start_lan()
                except Exception as e:
                    self.err_msg = f"Connect failed: {e}"; self.err_time = 180
        if key == pygame.K_ESCAPE: self.net.stop(); self._go(S_LAN)

    def _draw_lan_join(self):
        self._txtc("Searching for rooms...", 40, WHITE, self.fnl)
        if not self.net.found:
            dots = "." * (1 + (self.anim_t // 30) % 3)
            self._txtc(f"Scanning{dots}", 120, GRAY)
        else:
            for i, (ip, name) in enumerate(self.net.found):
                c = GOLD if i == self.lan_join_sel else WHITE
                p = "> " if i == self.lan_join_sel else "  "
                self._txt(f"{p}{name} ({ip})", 80, 100 + i * 40, c)
        self._txtc("Enter join  Esc back", 550, GRAY, self.fns)

    # ====== PLAY ======
    def _k_play(self, key):
        g = self.game
        if key == pygame.K_LEFT:  g.move(-1); self.das_dir = -1; self.das_delay = 0
        if key == pygame.K_RIGHT: g.move(1);  self.das_dir = 1;  self.das_delay = 0
        if key == pygame.K_UP:    g.rotate()
        if key == pygame.K_DOWN:  g.soft_drop()
        if key == pygame.K_SPACE: g.hard_drop()
        if key == pygame.K_ESCAPE: self._go(S_PAUSE); self.pause_sel = 0

    def _k_lan_play(self, key):
        g = self.game
        if key == pygame.K_LEFT:  g.move(-1); self.das_dir = -1; self.das_delay = 0
        if key == pygame.K_RIGHT: g.move(1);  self.das_dir = 1;  self.das_delay = 0
        if key == pygame.K_UP:    g.rotate()
        if key == pygame.K_DOWN:  g.soft_drop()
        if key == pygame.K_SPACE: g.hard_drop()
        if key == pygame.K_ESCAPE:
            self.net.send({"t":"over"}); self.vs_result = "lose"
            self.net.stop(); self._go(S_OVER)

    # ====== PAUSE ======
    def _k_pause(self, key):
        items = ["Resume","Save","Back to Menu"]
        if key == pygame.K_UP:   self.pause_sel = (self.pause_sel - 1) % len(items)
        if key == pygame.K_DOWN: self.pause_sel = (self.pause_sel + 1) % len(items)
        if key == pygame.K_RETURN:
            if self.pause_sel == 0: self._go(S_PLAY)
            elif self.pause_sel == 1:
                self.saves.save(self.game, 0)
                self.err_msg = "Saved!"; self.err_time = 90
            elif self.pause_sel == 2: self._go(S_MENU)
        if key == pygame.K_ESCAPE: self._go(S_PLAY)

    def _draw_pause(self):
        self._draw_play()
        ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA); ov.fill((0,0,0,160))
        self.screen.blit(ov, (0,0))
        self._txtc("Paused", 200, WHITE, self.fnl)
        self._draw_items(["Resume","Save","Back to Menu"], self.pause_sel, 280)

    # ====== OVER ======
    def _k_over(self, key):
        if key == pygame.K_r:
            m, sl = self.game.mode, self.game.start_level
            self.game = TetrisGame(m, sl); self._go(S_PLAY if self.state != S_OVER else S_PLAY)
            # 如果是联机模式按R则回到菜单
            if self.net.connected or self.net.is_host:
                self.net.stop(); self._go(S_MENU)
            else:
                self._go(S_PLAY)
        if key == pygame.K_ESCAPE: self.net.stop(); self._go(S_MENU)

    def _draw_over(self):
        if self.state == S_LAN_PLAY or self.vs_result:
            self._draw_lan_play()
            ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA); ov.fill((0,0,0,180))
            self.screen.blit(ov, (0,0))
            if self.vs_result == "win":
                self._txtc("Victory!", 220, (50,255,50), self.fnx)
            elif self.vs_result == "lose":
                self._txtc("Defeat", 220, (255,60,60), self.fnx)
            else:
                self._txtc("Game Over", 220, (255,60,60), self.fnx)
            self._txtc(f"Score: {self.game.score}", 300, WHITE, self.fnl)
            self._txtc("Esc back to menu", 380, GRAY)
        else:
            self._draw_play()
            ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA); ov.fill((0,0,0,180))
            self.screen.blit(ov, (0,0))
            if self.game.won:
                self._txtc("Cleared!", 220, (50,255,50), self.fnx)
            else:
                self._txtc("Game Over", 220, (255,60,60), self.fnx)
            self._txtc(f"Score: {self.game.score}", 300, WHITE, self.fnl)
            self._txtc(f"Lines: {self.game.lines}", 340, WHITE)
            self._txtc("R restart  Esc back to menu", 410, GRAY, self.fns)

    # ====== start game ======
    def _start_game(self, mode, start_level, data=None):
        self.game = TetrisGame(mode, start_level)
        if data: self.game.load_dict(data)
        self.das_dir = 0; self.das_delay = 0
        self.vs_result = ""
        self.W, self.H = 640, 640
        self.screen = pygame.display.set_mode((self.W, self.H))
        self._go(S_PLAY)

    def _load_game(self, data):
        mode = data.get("mode", 0)
        sl = data.get("start_level", 0)
        self.game = TetrisGame(mode, sl)
        self.game.load_dict(data)
        self.das_dir = 0; self.das_delay = 0
        self.W, self.H = 640, 640
        self.screen = pygame.display.set_mode((self.W, self.H))
        self._go(S_PLAY)

    def _start_lan(self):
        self.game = TetrisGame(M_CLASSIC, 0)
        self.opp_board = [[0]*COLS for _ in range(ROWS)]
        self.opp_score = self.opp_lines = 0
        self.opp_type = self.opp_rot = self.opp_x = self.opp_y = self.opp_next = 0
        self.das_dir = 0; self.das_delay = 0; self.send_tick = 0
        self.vs_result = ""
        self.W, self.H = 700, 640
        self.screen = pygame.display.set_mode((self.W, self.H))
        self._go(S_LAN_PLAY)

    # ====== update ======
    def _update(self):
        self.anim_t += 1
        if self.err_time > 0: self.err_time -= 1

        if self.state == S_PLAY and self.game:
            self.game.update()
            if self.game.over or self.game.won: self._go(S_OVER)
            # DAS
            if self.das_dir:
                keys = pygame.key.get_pressed()
                held = (self.das_dir == -1 and keys[pygame.K_LEFT]) or \
                       (self.das_dir == 1 and keys[pygame.K_RIGHT])
                if held:
                    self.das_delay += 1
                    if self.das_delay > 10 and self.das_delay % 3 == 0:
                        self.game.move(self.das_dir)
                else: self.das_dir = 0; self.das_delay = 0

        elif self.state == S_LAN_PLAY and self.game:
            self.game.update()
            # 处理网络消息
            for msg in self.net.get():
                if msg.get("t") == "state":
                    self.opp_board = msg["board"]
                    self.opp_score = msg.get("score", 0)
                    self.opp_lines = msg.get("lines", 0)
                    self.opp_type = msg.get("type", 0)
                    self.opp_rot = msg.get("rot", 0)
                    self.opp_x = msg.get("x", 0)
                    self.opp_y = msg.get("y", 0)
                    self.opp_next = msg.get("next", 0)
                elif msg.get("t") == "garbage":
                    self.game.add_garbage(msg["n"])
                elif msg.get("t") == "over":
                    if not self.vs_result: self.vs_result = "win"
            # 发送垃圾行
            if self.game.last_cleared >= 2:
                gn = [0,0,1,2,4][self.game.last_cleared]
                self.net.send({"t":"garbage","n":gn})
                self.game.last_cleared = 0
            # 发送状态
            self.send_tick += 1
            if self.send_tick >= 3:
                self.send_tick = 0
                self.net.send({"t":"state", **self.game.state_dict()})
            # DAS
            if self.das_dir:
                keys = pygame.key.get_pressed()
                held = (self.das_dir == -1 and keys[pygame.K_LEFT]) or \
                       (self.das_dir == 1 and keys[pygame.K_RIGHT])
                if held:
                    self.das_delay += 1
                    if self.das_delay > 10 and self.das_delay % 3 == 0:
                        self.game.move(self.das_dir)
                else: self.das_dir = 0; self.das_delay = 0
            # 检查游戏结束
            if self.game.over and not self.vs_result:
                self.vs_result = "lose"
                self.net.send({"t":"over"})
                self._go(S_OVER)
            # 检查断开
            if self.net.disconnected and not self.vs_result:
                self.vs_result = "lose"
                self.err_msg = "连接断开"; self.err_time = 300
                self._go(S_OVER)

    # ====== draw ======
    def _draw(self):
        self.screen.fill(BG)
        {S_MENU: self._draw_menu, S_LEVEL: self._draw_level,
         S_LOAD: self._draw_load, S_LAN: self._draw_lan,
         S_LAN_HOST: self._draw_lan_host, S_LAN_JOIN: self._draw_lan_join,
         S_PLAY: self._draw_play, S_LAN_PLAY: self._draw_lan_play,
         S_PAUSE: self._draw_pause, S_OVER: self._draw_over,
        }.get(self.state, lambda: None)()
        # 错误消息
        if self.err_time > 0:
            self._txtc(self.err_msg, self.H - 50, (255,100,100), self.fns)
        # 标题栏
        if self.state in (S_PLAY, S_LAN_PLAY, S_PAUSE, S_OVER):
            pygame.display.set_caption(f"Tetris - {MODE_NAMES[self.game.mode]}")

    # --- 单人游戏绘制 ---
    def _draw_play(self):
        g = self.game; ox, oy = 20, 20
        self._draw_board(g.board, ox, oy, CELL)
        self._draw_piece(g, ox, oy, CELL)
        # 侧边栏
        sx = ox + COLS*CELL + 24
        self._txt("Next", sx, 20, GRAY, self.fns)
        self._draw_next(g.next, sx, 44, CELL-4)
        self._txt(f"Score  {g.score}", sx, 160, WHITE)
        self._txt(f"Level  {g.level+1}", sx, 195, WHITE)
        self._txt(f"Lines  {g.lines}", sx, 230, WHITE)
        if g.mode == M_MARATHON:
            self._txt(f"Goal  {min(g.lines,150)}/150", sx, 265, GOLD, self.fns)
        if g.mode == M_ZEN:
            self._txt("Zen  no end", sx, 265, (100,200,255), self.fns)
        # 操作提示
        hy = 340
        for t in ["Arrows  Move","Up  Rotate","Down  Soft Drop","Space  Hard Drop","Esc  Pause"]:
            self._txt(t, sx, hy, GRAY, self.fns); hy += 22

    # --- 联机绘制 ---
    def _draw_lan_play(self):
        g = self.game
        c = CELL_LAN
        # 你的棋盘
        ox1, oy1 = 15, 55
        self._txt("You", ox1, 10, GOLD)
        self._txt(f"Score:{g.score} Lines:{g.lines}", ox1, 32, GRAY, self.fns)
        self._draw_board(g.board, ox1, oy1, c)
        self._draw_piece(g, ox1, oy1, c)
        # VS
        self._txtc("VS", 280, WHITE, self.fnl)
        # 对手棋盘
        ox2 = ox1 + COLS*c + 40
        self._txt("Rival", ox2, 10, (255,100,100))
        self._txt(f"Score:{self.opp_score} Lines:{self.opp_lines}", ox2, 32, GRAY, self.fns)
        if self.opp_board:
            self._draw_board(self.opp_board, ox2, oy1, c)
            # 对手当前方块
            for cx, cy in self._opp_cells():
                if cy >= 0:
                    clr = COLORS[self.opp_type+1]
                    r = pygame.Rect(ox2+cx*c+1, oy1+cy*c+1, c-2, c-2)
                    pygame.draw.rect(self.screen, clr, r)
        # 下一个方块
        self._txt("Next", ox2, oy1+ROWS*c+8, GRAY, self.fns)
        self._draw_next(g.next, ox2, oy1+ROWS*c+30, c-6)

    def _opp_cells(self):
        t, r, ox, oy = self.opp_type, self.opp_rot, self.opp_x, self.opp_y
        return [(dx+ox, dy+oy) for dx, dy in SHAPES[t][r]]

# ===================== main =====================
if __name__ == "__main__":
    App().run()
