import os
import pygame
import random
import sys
from collections import deque

pygame.init()

# Tamanho do tabuleiro (6x6) e dimensões de cada célula em pixels.
TAM      = 6
TILE     = 100
PANEL_W  = 240
W_SCR    = TAM * TILE + PANEL_W
H_SCR    = TAM * TILE

# Posição e direção iniciais do agente (canto inferior esquerdo, olhando para Leste).
START_R, START_C = 5, 0
START_DIR        = 1

# Vetores de movimento indexados por direção: 0=Norte, 1=Leste, 2=Sul, 3=Oeste.
DIRS      = [(-1,0),(0,1),(1,0),(0,-1)]
DIR_NAMES = ["Norte","Leste","Sul","Oeste"]
DIR_ARROW = ["^ ","->","v ","<-"]

# Quantidade de cada elemento gerado aleatoriamente no mundo.
NUM_WUMPUS = 2
NUM_PITS   = 4
NUM_GOLD   = 3
NUM_BATS   = 2

# Sistema de pontuação: cada ação custa -1, flecha extra -10, ouro +1000, morte -1000.
C_ACAO   = -1
C_FLECHA = -10
R_OURO   = 1000
C_MORTE  = -1000

COL_VISIBLE = (160, 205, 140)
COL_HIDDEN  = (28,  28,  28)
COL_GRID    = (0,   0,   0)
COL_START   = (255, 255, 140)
COL_PIT     = (55,  55,  65)
COL_WUMPUS  = (195, 40,  40)
COL_GOLD    = (255, 215,  0)
COL_BAT     = (120, 60,  180)
COL_AGENT   = (30,  100, 220)
COL_PANEL   = (22,  22,  32)
COL_TEXT    = (225, 225, 225)
COL_WARN    = (255, 80,  80)
COL_OK      = (100, 220, 100)
COL_BRISA   = (100, 190, 255)
COL_FEDOR   = (170, 130, 50)
COL_BRILHO  = (255, 245, 80)
COL_MORCEGO = (185, 130, 255)
COL_GRITO   = (255, 170, 170)

PERC_COR  = {"Brisa":COL_BRISA,"Fedor":COL_FEDOR,"Brilho":COL_BRILHO,
             "Gritos":COL_MORCEGO,"Grito":COL_GRITO,"Impacto":COL_WARN}
PERC_ICON = {"Brisa":"~","Fedor":"S","Brilho":"*",
             "Gritos":"P","Grito":"!","Impacto":"!"}


# Carrega uma imagem pelo nome (ou lista de nomes alternativos) e redimensiona.
# Funciona tanto ao rodar o código-fonte quanto no executável gerado pelo PyInstaller.
def load_img(names, size):
    if isinstance(names, str):
        names = [names]
    folders = []
    if getattr(sys, "frozen", False):
        # one-file: recursos extraidos em _MEIPASS; one-dir: ao lado do exe
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            folders.append(meipass)
        folders.append(os.path.dirname(sys.executable))
    else:
        folders.append(os.path.dirname(os.path.abspath(__file__)))
    dl   = os.path.join(os.path.expanduser("~"), "Downloads")
    folders.append(dl)

    for n in names:
        for folder in folders:
            path = os.path.join(folder, n)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    return pygame.transform.smoothscale(img, size)
                except Exception as e:
                    print(f"Erro ao carregar {path}: {e}")
    return None

SZ  = (TILE - 18, TILE - 18)
SZA = (TILE - 24, TILE - 24)

tela      = pygame.display.set_mode((W_SCR, H_SCR))
pygame.display.set_caption("Mundo do Wumpus 6x6")

font       = pygame.font.SysFont("Arial", 17)
font_bold  = pygame.font.SysFont("Arial", 18, bold=True)
font_small = pygame.font.SysFont("Arial", 13)
font_title = pygame.font.SysFont("Arial", 21, bold=True)

img_pit    = load_img("pit.png",    SZ)
img_wumpus = load_img("wumpus.png", SZ)
img_gold   = load_img("gold.png",   SZ)
img_agent  = load_img("agent.png",  SZA)
img_bat    = load_img(["morcego.png", "bat.png", "morcego2.png"], SZ)


# Gera o mapa aleatório: posiciona poços, wumpus, ouro e morcegos com regras de exclusão.
def criar_mundo():
    # Cada célula é um conjunto de tokens: "P"=poço, "O"=ouro, "B"=morcego.
    celulas = [[set() for _ in range(TAM)] for _ in range(TAM)]

    # Zona segura inicial: célula de saída e vizinhos ortogonais.
    # Nenhum perigo (poço, wumpus, morcego) pode nascer aqui.
    safe_start_zone = {(START_R, START_C)}
    for dr, dc in DIRS:
        nr, nc = START_R + dr, START_C + dc
        if 0 <= nr < TAM and 0 <= nc < TAM:
            safe_start_zone.add((nr, nc))

    def perto_start(r, c):
        # Impede que wumpus apareça imediatamente ao lado da saída.
        return max(abs(r - START_R), abs(c - START_C)) <= 1

    todas = [(r, c) for r in range(TAM) for c in range(TAM)
             if (r, c) != (START_R, START_C)]
    random.shuffle(todas)

    # Coloca os poços em posições aleatórias.
    pits = set()
    for pos in todas:
        if len(pits) >= NUM_PITS:
            break
        if pos in safe_start_zone:
            continue
        pits.add(pos)
    for r, c in pits:
        celulas[r][c].add("P")

    # Wumpus fica longe da saída (e nunca em cima de poço ou zona segura inicial).
    cand_w = [p for p in todas if p not in pits and p not in safe_start_zone and not perto_start(*p)]
    if len(cand_w) < NUM_WUMPUS:
        cand_w = [p for p in todas if p not in pits and p not in safe_start_zone]
    random.shuffle(cand_w)
    wumpus_list = cand_w[:NUM_WUMPUS]

    # Ouro não pode compartilhar célula com poço, wumpus ou zona segura inicial.
    used_w = set(wumpus_list)
    cand_o = [p for p in todas if p not in pits and p not in used_w and p not in safe_start_zone]
    random.shuffle(cand_o)
    gold_pos = set()
    for i in range(min(NUM_GOLD, len(cand_o))):
        r, c = cand_o[i]
        celulas[r][c].add("O")
        gold_pos.add((r, c))

    # Morcego não pode compartilhar célula com poço, ouro, wumpus ou zona segura inicial.
    cand_b = [
        p for p in todas
        if p not in pits and p not in gold_pos and p not in used_w and p not in safe_start_zone
    ]
    random.shuffle(cand_b)
    for i in range(min(NUM_BATS, len(cand_b))):
        r, c = cand_b[i]
        celulas[r][c].add("B")

    return celulas, list(wumpus_list)


class Jogo:
    def __init__(self):
        self.reset()

    # Reinicia o jogo com um novo mundo aleatório, resetando todas as variáveis de estado.
    def reset(self):
        self.celulas, self.wumpuses = criar_mundo()
        self.wumpus_vivo = [True] * len(self.wumpuses)
        self.r         = START_R
        self.c         = START_C
        self.dir       = START_DIR
        self.vivo      = True
        self.saiu      = False
        self.score     = 0
        self.ouro      = 0
        self.flecha    = True   # O agente começa com uma única flecha.
        self.visitados = set()  # Células já visitadas (reveladas no mapa).
        self.perc_map  = {}     # Percepções salvas por célula visitada.
        self.msg       = ("", COL_TEXT)
        self._grito    = False
        self.impacto   = False
        self._visitar(START_R, START_C)

    # Marca a célula como visitada e calcula suas percepções.
    def _visitar(self, r, c):
        self.visitados.add((r, c))
        self.perc_map[(r, c)] = self._perceber(r, c)

    # Calcula as percepções de uma célula: Brisa (poço vizinho), Fedor (wumpus vizinho),
    # Gritos (morcego vizinho) e Brilho (ouro na própria célula).
    def _perceber(self, r, c):
        p = set()
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < TAM and 0 <= nc < TAM:
                if "P" in self.celulas[nr][nc]:
                    p.add("Brisa")
                for i, (wr, wc) in enumerate(self.wumpuses):
                    if (wr, wc) == (nr, nc) and self.wumpus_vivo[i]:
                        p.add("Fedor")
                if "B" in self.celulas[nr][nc]:
                    p.add("Gritos")
        if "O" in self.celulas[r][c]:
            p.add("Brilho")
        return frozenset(p)

    def perceber_atual(self):
        p = set(self._perceber(self.r, self.c))
        if self.impacto:
            p.add("Impacto")
        if self._grito:
            p.add("Grito")
        return p

    def _custo(self, extra=0):
        self.score  += C_ACAO + extra
        self.impacto = False
        self._grito  = False

    def _msg(self, texto, cor=COL_TEXT):
        self.msg = (texto, cor)

    # Move o agente uma célula para frente na direção atual.
    # Se bater na parede, gera percepção de Impacto.
    def mover(self):
        if not self.vivo or self.saiu:
            return
        self._custo()
        dr, dc = DIRS[self.dir]
        nr, nc = self.r + dr, self.c + dc
        if 0 <= nr < TAM and 0 <= nc < TAM:
            self.r, self.c = nr, nc
            self._visitar(nr, nc)
            self._check_sala()  # Verifica perigo na nova célula.
        else:
            self.impacto = True
            self._msg("Impacto! Ha uma parede a frente.", COL_WARN)

    def virar_direita(self):
        if not self.vivo or self.saiu:
            return
        self._custo()
        self.dir = (self.dir + 1) % 4

    def virar_esquerda(self):
        if not self.vivo or self.saiu:
            return
        self._custo()
        self.dir = (self.dir - 1) % 4

    def pegar(self):
        if not self.vivo or self.saiu:
            return
        self._custo()
        if "O" in self.celulas[self.r][self.c]:
            self.celulas[self.r][self.c].discard("O")
            self.ouro  += 1
            self.score += R_OURO
            self.perc_map[(self.r, self.c)] = self._perceber(self.r, self.c)
            self._msg(f"Ouro coletado! +{R_OURO} pontos", COL_GOLD)
        else:
            self._msg("Nada para pegar aqui.", COL_TEXT)

    # Atira a única flecha em linha reta na direção atual.
    # Se atingir um wumpus: marca como morto, atualiza percepções dos vizinhos e gera "Grito".
    def atirar(self):
        if not self.vivo or self.saiu:
            return
        if not self.flecha:
            self._msg("Sem flechas!", COL_WARN)
            return
        self._custo(extra=C_FLECHA)
        self.flecha = False
        dr, dc = DIRS[self.dir]
        r, c   = self.r + dr, self.c + dc
        acertou = False
        while 0 <= r < TAM and 0 <= c < TAM:  # Percorre todas as células na linha de tiro.
            for i, (wr, wc) in enumerate(self.wumpuses):
                if (wr, wc) == (r, c) and self.wumpus_vivo[i]:
                    self.wumpus_vivo[i] = False
                    self._grito = True
                    acertou = True
                    self._msg("GRITO! Wumpus abatido!", COL_OK)
                    # Atualiza Fedor nas células vizinhas ao wumpus morto.
                    for dr2, dc2 in DIRS:
                        nr2, nc2 = wr + dr2, wc + dc2
                        if (nr2, nc2) in self.visitados:
                            self.perc_map[(nr2, nc2)] = self._perceber(nr2, nc2)
                    break
            if acertou:
                break
            r, c = r + dr, c + dc
        if not acertou:
            self._msg("Flecha errou.", COL_TEXT)

    def subir(self):
        if not self.vivo or self.saiu:
            return
        self._custo()
        if (self.r, self.c) == (START_R, START_C):
            self.saiu = True
            self._msg(f"Saiu com vida! Score: {self.score}", COL_OK)
        else:
            self._msg("Saida so em [1,1] (canto inf. esq.).", COL_WARN)

    # Verifica o que há na célula atual: morcego (teleporte), poço ou wumpus (morte).
    def _check_sala(self):
        r, c = self.r, self.c
        if "B" in self.celulas[r][c]:
            self._bat_teleport(r, c)
            return
        if "P" in self.celulas[r][c]:
            self.vivo   = False
            self.score += C_MORTE
            self._msg("Caiu num poco! -1000", COL_WARN)
            return
        for i, (wr, wc) in enumerate(self.wumpuses):
            if (wr, wc) == (r, c) and self.wumpus_vivo[i]:
                self.vivo   = False
                self.score += C_MORTE
                self._msg("Devorado pelo Wumpus! -1000", COL_WARN)
                return

    # Teleporta o agente para uma célula aleatória (comportamento do morcego).
    # Encadeia teleportes se cair em outro morcego (limite de 5 para evitar loop infinito).
    def _bat_teleport(self, bat_r, bat_c, depth=0):
        if depth > 5:
            return
        dest_r = random.randint(0, TAM - 1)
        dest_c = random.randint(0, TAM - 1)
        self.r, self.c = dest_r, dest_c
        self._visitar(dest_r, dest_c)
        if depth == 0:
            self._msg("Um morcego te carregou para outro lugar!", COL_MORCEGO)
        if "B" in self.celulas[dest_r][dest_c] and (dest_r, dest_c) != (bat_r, bat_c):
            self._bat_teleport(dest_r, dest_c, depth + 1)
            return
        if "P" in self.celulas[dest_r][dest_c]:
            self.vivo   = False
            self.score += C_MORTE
            self._msg("Teleportado para um poco! -1000", COL_WARN)
        else:
            for i, (wr, wc) in enumerate(self.wumpuses):
                if (wr, wc) == (dest_r, dest_c) and self.wumpus_vivo[i]:
                    self.vivo   = False
                    self.score += C_MORTE
                    self._msg("Teleportado para o Wumpus! -1000", COL_WARN)
                    break


jogo = Jogo()


class AutoPlayer:
    # IA simples baseada em risco: explora fronteira conhecida, coleta ouro e tenta voltar para sair.
    def __init__(self, jogo):
        self.jogo = jogo
        self.queue = deque()
        self.stuck_count = 0

    def reset(self):
        self.queue.clear()
        self.stuck_count = 0

    def _neighbors(self, r, c):
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < TAM and 0 <= nc < TAM:
                yield nr, nc

    def _path(self, start, goal, allowed):
        q = deque([start])
        prev = {start: None}
        while q:
            cur = q.popleft()
            if cur == goal:
                break
            for nb in self._neighbors(*cur):
                if nb in allowed and nb not in prev:
                    prev[nb] = cur
                    q.append(nb)
        if goal not in prev:
            return None
        p = []
        cur = goal
        while cur is not None:
            p.append(cur)
            cur = prev[cur]
        p.reverse()
        return p

    def _turn_steps(self, cur_dir, wanted_dir):
        right = (wanted_dir - cur_dir) % 4
        left = (cur_dir - wanted_dir) % 4
        if right <= left:
            return ["R"] * right
        return ["L"] * left

    def _enqueue_path(self, path):
        d = self.jogo.dir
        for i in range(1, len(path)):
            r0, c0 = path[i - 1]
            r1, c1 = path[i]
            dr, dc = r1 - r0, c1 - c0
            wanted = DIRS.index((dr, dc))
            turns = self._turn_steps(d, wanted)
            for t in turns:
                self.queue.append(t)
            self.queue.append("M")
            d = wanted

    def _aligned_dir(self, r, c, tr, tc):
        if r == tr:
            return 1 if tc > c else 3 if tc < c else None
        if c == tc:
            return 2 if tr > r else 0 if tr < r else None
        return None

    # Inferência conservadora: só marca alvo quando há certeza lógica pela percepção de Fedor.
    def _certain_wumpus_targets(self):
        visited = set(self.jogo.visitados)
        no_wumpus = set(visited)

        # Células adjacentes a uma casa sem Fedor não podem conter Wumpus vivo.
        for rc in visited:
            percs = self.jogo.perc_map.get(rc, frozenset())
            if "Fedor" not in percs:
                no_wumpus.update(self._neighbors(*rc))

        possible = {(r, c) for r in range(TAM) for c in range(TAM)} - no_wumpus
        certain = set()

        # Regra local: se uma casa com Fedor tiver apenas 1 vizinho possível, é alvo certo.
        stench_cells = []
        for rc in visited:
            percs = self.jogo.perc_map.get(rc, frozenset())
            if "Fedor" in percs:
                stench_cells.append(rc)
                opts = [nb for nb in self._neighbors(*rc) if nb in possible and nb not in visited]
                if len(opts) == 1:
                    certain.add(opts[0])

        # Regra de interseção: se todas as casas com Fedor convergem para uma única célula.
        if stench_cells:
            inter = set(possible)
            for rc in stench_cells:
                inter &= set(self._neighbors(*rc))
            if len(inter) == 1:
                certain.update(inter)

        return certain

    def _enqueue_shot_if_certain(self):
        if not self.jogo.flecha:
            return False

        targets = list(self._certain_wumpus_targets())
        if not targets:
            return False

        r, c = self.jogo.r, self.jogo.c

        # 1) Tenta tiro direto da posição atual.
        direct = []
        for tr, tc in targets:
            d = self._aligned_dir(r, c, tr, tc)
            if d is not None:
                dist = abs(tr - r) + abs(tc - c)
                direct.append((dist, d))
        if direct:
            _dist, d = min(direct, key=lambda x: x[0])
            for t in self._turn_steps(self.jogo.dir, d):
                self.queue.append(t)
            self.queue.append("F")
            return True

        # 2) Se não estiver alinhado, reposiciona para uma célula visitada alinhada e então atira.
        visited = set(self.jogo.visitados)
        options = []
        for vr, vc in visited:
            for tr, tc in targets:
                d = self._aligned_dir(vr, vc, tr, tc)
                if d is None:
                    continue
                path = self._path((r, c), (vr, vc), visited)
                if path:
                    options.append((len(path) - 1, path, d))

        if not options:
            return False

        _cost, path, d = min(options, key=lambda x: x[0])
        self._enqueue_path(path)

        dir_after = self.jogo.dir
        if len(path) > 1:
            r0, c0 = path[-2]
            r1, c1 = path[-1]
            dir_after = DIRS.index((r1 - r0, c1 - c0))

        for t in self._turn_steps(dir_after, d):
            self.queue.append(t)
        self.queue.append("F")
        return True

    def _risk_map(self):
        risk = {(r, c): 0 for r in range(TAM) for c in range(TAM)}
        safe = set(self.jogo.visitados)

        for rc in self.jogo.visitados:
            percs = self.jogo.perc_map.get(rc, frozenset())
            nbs = list(self._neighbors(*rc))

            # Sem sinais de perigo no entorno: vizinhos são fortes candidatos a seguro.
            if "Brisa" not in percs and "Fedor" not in percs and "Gritos" not in percs:
                safe.update(nbs)

            for nb in nbs:
                if nb in self.jogo.visitados:
                    continue
                if "Brisa" in percs:
                    risk[nb] += 3
                if "Fedor" in percs:
                    risk[nb] += 4
                if "Gritos" in percs:
                    risk[nb] += 2

        for rc in safe:
            risk[rc] -= 5

        return risk, safe

    def _enqueue_plan(self):
        if not self.jogo.vivo or self.jogo.saiu:
            return

        r, c = self.jogo.r, self.jogo.c
        visited = set(self.jogo.visitados)

        # Objetivo cumprido: com todo o ouro coletado, prioriza voltar para a saída.
        if self.jogo.ouro >= NUM_GOLD:
            if (r, c) == (START_R, START_C):
                self.queue.append("E")
                self.stuck_count = 0
                return
            back = self._path((r, c), (START_R, START_C), set(self.jogo.visitados))
            if back and len(back) > 1:
                self._enqueue_path(back)
                self.stuck_count = 0
                return

        if "O" in self.jogo.celulas[r][c]:
            self.queue.append("G")
            self.stuck_count = 0
            return

        # Prioridade alta: se já conhece ouro não coletado, vai buscá-lo antes de explorar risco.
        known_gold = [(gr, gc) for (gr, gc) in visited if "O" in self.jogo.celulas[gr][gc]]
        if known_gold:
            target = min(known_gold, key=lambda p: abs(p[0] - r) + abs(p[1] - c))
            path_to_gold = self._path((r, c), target, visited | {target})
            if path_to_gold and len(path_to_gold) > 1:
                self._enqueue_path(path_to_gold)
                self.stuck_count = 0
                return

        # Se houver posição certa de Wumpus, tenta usar a flecha estrategicamente.
        if self._enqueue_shot_if_certain():
            self.stuck_count = 0
            return

        risk, _safe = self._risk_map()

        frontier = set()
        for vr, vc in visited:
            for nb in self._neighbors(vr, vc):
                if nb not in visited:
                    frontier.add(nb)

        # Se não há fronteira segura aparente, retorna para saída e tenta encerrar.
        if not frontier:
            if (r, c) == (START_R, START_C):
                self.queue.append("E")
                self.stuck_count = 0
                return
            back = self._path((r, c), (START_R, START_C), visited)
            if back:
                self._enqueue_path(back)
                self.stuck_count = 0
            return

        candidates = sorted(frontier, key=lambda p: (risk[p], abs(p[0] - r) + abs(p[1] - c)))

        # Tenta encontrar caminho para algum candidato (não só o melhor), evitando travar em um alvo impossível.
        for cand in candidates:
            allowed = set(visited)
            allowed.update({p for p in frontier if risk[p] <= risk[cand] + 1})
            allowed.add(cand)
            path = self._path((r, c), cand, allowed)
            if path and len(path) > 1:
                self._enqueue_path(path)
                self.stuck_count = 0
                return

        # Se não há caminho, tenta avançar para um vizinho desconhecido de menor risco.
        unknown_adj = [nb for nb in self._neighbors(r, c) if nb not in visited]
        if unknown_adj:
            target = min(unknown_adj, key=lambda p: risk[p])
            if risk[target] <= 8 or self.stuck_count >= 2:
                dr, dc = target[0] - r, target[1] - c
                wanted = DIRS.index((dr, dc))
                for t in self._turn_steps(self.jogo.dir, wanted):
                    self.queue.append(t)
                self.queue.append("M")
                self.stuck_count = 0
                return

        # Último recurso: volta para a saída e encerra a rodada para não ficar girando indefinidamente.
        if (r, c) != (START_R, START_C):
            back = self._path((r, c), (START_R, START_C), visited)
            if back and len(back) > 1:
                self._enqueue_path(back)
                self.stuck_count = 0
                return
        else:
            self.queue.append("E")
            self.stuck_count = 0
            return

        self.stuck_count += 1
        self.queue.append("R")

    def step(self):
        if not self.jogo.vivo or self.jogo.saiu:
            return

        # Interrompe qualquer plano para pegar ouro imediatamente ao entrar na célula.
        if "O" in self.jogo.celulas[self.jogo.r][self.jogo.c]:
            self.queue.clear()
            self.jogo.pegar()
            return

        if not self.queue:
            self._enqueue_plan()

        if not self.queue:
            return

        action = self.queue.popleft()
        if action == "M":
            self.jogo.mover()
        elif action == "R":
            self.jogo.virar_direita()
        elif action == "L":
            self.jogo.virar_esquerda()
        elif action == "G":
            self.jogo.pegar()
        elif action == "F":
            self.jogo.atirar()
        elif action == "E":
            self.jogo.subir()


auto_player = AutoPlayer(jogo)

MODE_MENU = "menu"
MODE_AUTO = "auto"
MODE_TEST = "test"

modo_atual = MODE_MENU
last_auto_tick = 0
AUTO_DELAY_MS = 220
auto_pausado = False


def _draw_item(surf, key, img, cor, px, py, w, h):
    if img:
        s = pygame.transform.smoothscale(img, (max(1, w), max(1, h)))
        surf.blit(s, (px, py))
    else:
        if key == "B":
            # Fallback visual para morcego quando a imagem nao esta disponivel.
            cx, cy = px + w // 2, py + h // 2
            points = [
                (cx - w // 2 + 4, cy + h // 8),
                (cx - w // 3, cy - h // 5),
                (cx - w // 6, cy),
                (cx, cy - h // 6),
                (cx + w // 6, cy),
                (cx + w // 3, cy - h // 5),
                (cx + w // 2 - 4, cy + h // 8),
                (cx + w // 4, cy + h // 5),
                (cx, cy + h // 3),
                (cx - w // 4, cy + h // 5),
            ]
            pygame.draw.polygon(surf, (20, 20, 20), points)
        else:
            pygame.draw.rect(surf, cor, (px + 2, py + 2, w - 4, h - 4), border_radius=5)
            lbl = font_small.render(key, True, COL_TEXT)
            surf.blit(lbl, (px + w // 2 - lbl.get_width() // 2,
                            py + h // 2 - lbl.get_height() // 2))


def _draw_agent(surf, rx, ry, dire):
    if img_agent:
        if dire == 3:
            # Esquerda: usa exatamente a PNG original.
            rot = img_agent
        elif dire == 1:
            # Direita: usa a versao espelhada da PNG.
            rot = pygame.transform.flip(img_agent, True, False)
        elif dire == 0:
            # Cima.
            rot = pygame.transform.rotate(img_agent, -90)
        else:
            # Baixo.
            rot = pygame.transform.rotate(img_agent, 90)
        ax    = rx + (TILE - rot.get_width())  // 2
        ay    = ry + (TILE - rot.get_height()) // 2
        surf.blit(rot, (ax, ay))
    else:
        cx, cy = rx + TILE // 2, ry + TILE // 2
        sz     = TILE // 3
        pts_list = [
            [(cx, cy-sz),(cx-sz//2,cy+sz//2),(cx+sz//2,cy+sz//2)],
            [(cx+sz,cy),(cx-sz//2,cy-sz//2),(cx-sz//2,cy+sz//2)],
            [(cx,cy+sz),(cx-sz//2,cy-sz//2),(cx+sz//2,cy-sz//2)],
            [(cx-sz,cy),(cx+sz//2,cy-sz//2),(cx+sz//2,cy+sz//2)],
        ]
        pygame.draw.polygon(surf, COL_AGENT, pts_list[dire])


# Desenha uma única célula do tabuleiro: fundo, ícones dos elementos e percepções.
# Células não visitadas ficam escuras (fog of war); ao morrer/sair tudo é revelado.
def draw_cell(surf, jogo, r, c):
    rx, ry     = c * TILE, r * TILE
    reveal_all = not jogo.vivo or jogo.saiu
    visible    = (r, c) in jogo.visitados or reveal_all
    is_here    = (r == jogo.r and c == jogo.c)

    bg = COL_VISIBLE if visible else COL_HIDDEN
    pygame.draw.rect(surf, bg, (rx, ry, TILE, TILE))

    if (r, c) == (START_R, START_C):
        pygame.draw.rect(surf, COL_START, (rx + 1, ry + 1, TILE - 2, TILE - 2), 3)
        lbl = font_small.render("SAIDA [1,1]", True, (140, 120, 0))
        surf.blit(lbl, (rx + TILE // 2 - lbl.get_width() // 2, ry + 3))

    if visible:
        items = []
        if "P" in jogo.celulas[r][c]:
            items.append(("P", img_pit,    COL_PIT))
        for i, (wr, wc) in enumerate(jogo.wumpuses):
            if (wr, wc) == (r, c) and jogo.wumpus_vivo[i]:
                items.append(("W", img_wumpus, COL_WUMPUS))
        if "O" in jogo.celulas[r][c]:
            items.append(("O", img_gold,   COL_GOLD))
        if "B" in jogo.celulas[r][c]:
            items.append(("B", img_bat,    COL_BAT))

        n = len(items)
        if n == 1:
            _draw_item(surf, *items[0], rx + 9, ry + 9, TILE - 18, TILE - 18)
        elif n == 2:
            h2 = TILE // 2 - 6
            _draw_item(surf, *items[0], rx + 4,             ry + 9, h2, TILE - 18)
            _draw_item(surf, *items[1], rx + TILE // 2 + 2, ry + 9, h2, TILE - 18)
        elif n >= 3:
            q  = TILE // 2 - 6
            ps = [(rx + 4, ry + 4), (rx + TILE//2 + 2, ry + 4),
                  (rx + 4, ry + TILE//2 + 2), (rx + TILE//2 + 2, ry + TILE//2 + 2)]
            for idx2, it in enumerate(items[:4]):
                _draw_item(surf, *it, ps[idx2][0], ps[idx2][1], q, q)

        percs = jogo.perc_map.get((r, c), frozenset())
        bx = rx + 3
        by = ry + TILE - 15
        for p in sorted(percs):
            icon = PERC_ICON.get(p, p[0])
            s    = font_small.render(icon, True, PERC_COR.get(p, COL_TEXT))
            surf.blit(s, (bx, by))
            bx  += s.get_width() + 2

    if is_here:
        if jogo.vivo:
            _draw_agent(surf, rx, ry, jogo.dir)
        else:
            pygame.draw.line(surf, COL_WARN, (rx+10, ry+10), (rx+TILE-10, ry+TILE-10), 4)
            pygame.draw.line(surf, COL_WARN, (rx+TILE-10, ry+10), (rx+10, ry+TILE-10), 4)

    pygame.draw.rect(surf, COL_GRID, (rx, ry, TILE, TILE), 1)


# Desenha o painel lateral com score, posição, percepções atuais, controles e mensagem.
def draw_panel(surf, jogo):
    global modo_atual, auto_pausado
    px0 = TAM * TILE
    pygame.draw.rect(surf, COL_PANEL, (px0, 0, PANEL_W, H_SCR))
    px = px0 + 10
    py = [8]

    def line(text, cor=COL_TEXT, f=None):
        s = (f or font).render(text, True, cor)
        surf.blit(s, (px, py[0]))
        py[0] += s.get_height() + 3

    def sep():
        py[0] += 4
        pygame.draw.line(surf, (70, 70, 80),
                         (px0 + 5, py[0]), (px0 + PANEL_W - 5, py[0]))
        py[0] += 5

    line("WUMPUS WORLD", COL_GOLD, font_title)
    sep()
    line(f"Score: {jogo.score}", COL_GOLD)
    line(f"Ouro: {jogo.ouro} / {NUM_GOLD}")
    flecha_str = "SIM" if jogo.flecha else "NAO"
    line(f"Flecha: {flecha_str}", COL_OK if jogo.flecha else COL_WARN)
    row_d = TAM - jogo.r
    col_d = jogo.c + 1
    line(f"Posicao: [{row_d},{col_d}]")
    line(f"Direcao: {DIR_ARROW[jogo.dir]} {DIR_NAMES[jogo.dir]}")
    sep()
    line("PERCEPCOES:", COL_TEXT, font_bold)
    percs = jogo.perceber_atual()
    if percs:
        for p in sorted(percs):
            icon = PERC_ICON.get(p, "?")
            line(f"  {icon} {p}", PERC_COR.get(p, COL_TEXT))
    else:
        line("  (Nenhuma)", (150, 150, 150))
    sep()
    line("CONTROLES:", COL_TEXT, font_bold)
    controles = [
        ("W / seta cima",  "Mover para frente"),
        ("D / seta dir",   "Virar a direita"),
        ("A / seta esq",   "Virar a esquerda"),
        ("G",              "Pegar objeto"),
        ("F",              "Atirar flecha"),
        ("E / Enter",      "Subir (sair)"),
        ("R",              "Reiniciar"),
    ]
    for k, v in controles:
        ks = font_small.render(k,      True, COL_GOLD)
        vs = font_small.render(f" {v}", True, COL_TEXT)
        surf.blit(ks, (px, py[0]))
        surf.blit(vs, (px + ks.get_width(), py[0]))
        py[0] += ks.get_height() + 2

    if modo_atual == MODE_AUTO:
        sep()
        line("MODO COMPUTADOR", COL_OK, font_bold)
        line("ENTER: pausar/continuar", COL_TEXT)
        line("R: reiniciar", COL_TEXT)
        state = "PAUSADO" if auto_pausado else "RODANDO"
        line(f"Estado: {state}", COL_WARN if auto_pausado else COL_OK)

    if jogo.msg[0]:
        sep()
        texto, cor_m = jogo.msg
        max_w = PANEL_W - 20
        words = texto.split()
        cur   = ""
        for w in words:
            test = cur + w + " "
            if font.size(test)[0] > max_w:
                if cur:
                    line(cur.strip(), cor_m)
                cur = w + " "
            else:
                cur = test
        if cur:
            line(cur.strip(), cor_m)

    if not jogo.vivo or jogo.saiu:
        ov = pygame.Surface((TAM * TILE, H_SCR), pygame.SRCALPHA)
        ov.fill((180, 0, 0, 90) if not jogo.vivo else (0, 150, 0, 90))
        surf.blit(ov, (0, 0))
        if not jogo.vivo:
            m1 = font_title.render("GAME OVER", True, COL_WARN)
            m2 = font.render("Pressione R para reiniciar", True, COL_TEXT)
        else:
            m1 = font_title.render(f"VITORIA! {jogo.ouro} ouros", True, COL_GOLD)
            m2 = font.render(f"Score: {jogo.score}  |  R = reiniciar", True, COL_TEXT)
        surf.blit(m1, (TAM*TILE//2 - m1.get_width()//2, H_SCR//2 - 30))
        surf.blit(m2, (TAM*TILE//2 - m2.get_width()//2, H_SCR//2 + 10))


def draw_menu(surf):
    surf.fill((18, 24, 30))

    title = font_title.render("Mundo do Wumpus", True, COL_GOLD)
    sub = font.render("Escolha o modo", True, COL_TEXT)
    surf.blit(title, (W_SCR // 2 - title.get_width() // 2, 90))
    surf.blit(sub, (W_SCR // 2 - sub.get_width() // 2, 125))

    bw, bh = 320, 80
    bx = W_SCR // 2 - bw // 2
    rect_auto = pygame.Rect(bx, 200, bw, bh)
    rect_test = pygame.Rect(bx, 320, bw, bh)

    pygame.draw.rect(surf, (40, 120, 70), rect_auto, border_radius=10)
    pygame.draw.rect(surf, (70, 90, 150), rect_test, border_radius=10)

    t1 = font_bold.render("Jogo normal (computador joga)", True, COL_TEXT)
    t2 = font_bold.render("Testar (jogar manual)", True, COL_TEXT)
    surf.blit(t1, (rect_auto.centerx - t1.get_width() // 2,
                   rect_auto.centery - t1.get_height() // 2))
    surf.blit(t2, (rect_test.centerx - t2.get_width() // 2,
                   rect_test.centery - t2.get_height() // 2))

    hint = font_small.render("Clique em um modo ou use teclas 1 e 2", True, (190, 190, 190))
    surf.blit(hint, (W_SCR // 2 - hint.get_width() // 2, 430))

    pygame.display.flip()
    return rect_auto, rect_test


def desenhar(jogo):
    tela.fill(COL_HIDDEN)
    for r in range(TAM):
        for c in range(TAM):
            draw_cell(tela, jogo, r, c)
    draw_panel(tela, jogo)
    pygame.display.flip()


# Loop principal: captura teclas, executa ação no jogo e redesenha a tela a 60 FPS.
clock = pygame.time.Clock()
while True:
    rect_auto = None
    rect_test = None
    if modo_atual == MODE_MENU:
        rect_auto, rect_test = draw_menu(tela)

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if modo_atual == MODE_MENU:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_1:
                    jogo.reset()
                    auto_player.reset()
                    auto_pausado = False
                    modo_atual = MODE_AUTO
                    last_auto_tick = pygame.time.get_ticks()
                elif ev.key == pygame.K_2:
                    jogo.reset()
                    auto_player.reset()
                    auto_pausado = False
                    modo_atual = MODE_TEST
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if rect_auto and rect_auto.collidepoint(ev.pos):
                    jogo.reset()
                    auto_player.reset()
                    auto_pausado = False
                    modo_atual = MODE_AUTO
                    last_auto_tick = pygame.time.get_ticks()
                elif rect_test and rect_test.collidepoint(ev.pos):
                    jogo.reset()
                    auto_player.reset()
                    auto_pausado = False
                    modo_atual = MODE_TEST
            continue

        if ev.type == pygame.KEYDOWN:
            k = ev.key
            if modo_atual == MODE_TEST:
                if k == pygame.K_ESCAPE:
                    modo_atual = MODE_MENU
                    continue
                if   k in (pygame.K_w, pygame.K_UP):      jogo.mover()
                elif k in (pygame.K_d, pygame.K_RIGHT):   jogo.virar_direita()
                elif k in (pygame.K_a, pygame.K_LEFT):    jogo.virar_esquerda()
                elif k == pygame.K_g:                     jogo.pegar()
                elif k == pygame.K_f:                     jogo.atirar()
                elif k in (pygame.K_e, pygame.K_RETURN):  jogo.subir()
                elif k == pygame.K_r:
                    jogo.reset()
                    auto_player.reset()
            elif modo_atual == MODE_AUTO:
                if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    auto_pausado = not auto_pausado
                    jogo._msg("Modo auto pausado." if auto_pausado else "Modo auto retomado.", COL_OK)
                elif k == pygame.K_r:
                    jogo.reset()
                    auto_player.reset()
                    auto_pausado = False

    if modo_atual == MODE_AUTO and (not auto_pausado) and jogo.vivo and not jogo.saiu:
        now = pygame.time.get_ticks()
        if now - last_auto_tick >= AUTO_DELAY_MS:
            auto_player.step()
            last_auto_tick = now

    if modo_atual != MODE_MENU:
        desenhar(jogo)

    clock.tick(60)
