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

# Posição e direção iniciais do agente padrão (canto inferior esquerdo, olhando para Leste).
START_R, START_C = 5, 0
START_DIR        = 1

# No modo ajudante, o Heroi 1 nasce no canto inferior direito e a saida
# compartilhada dos dois fica nessa mesma celula.
HELPER_STARTS    = [(5, 5), (5, 0)]
HELPER_DIRS      = [3, 1]
HELPER_EXIT      = HELPER_STARTS[1]

# Vetores de movimento indexados por direção: 0=Norte, 1=Leste, 2=Sul, 3=Oeste.
DIRS      = [(-1,0),(0,1),(1,0),(0,-1)]
DIR_NAMES = ["Norte","Leste","Sul","Oeste"]
DIR_ARROW = ["^ ","->","v ","<-"]

# Quantidade de cada elemento gerado aleatoriamente no mundo.
NUM_WUMPUS = 2
NUM_PITS   = 4
NUM_GOLD   = 3
NUM_BATS   = 2
HELPER_GOLD = NUM_GOLD + 1
HELPER_WUMPUS = NUM_WUMPUS + 1

# Sistema de pontuação: cada ação custa -1, flecha extra -10, ouro +1000, morte -1000.
C_ACAO   = -1
C_FLECHA = -10
R_OURO   = 1000
C_MORTE  = -1000
R_OURO_AJUDANTE = R_OURO * 2

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
def criar_mundo(starts=None, num_wumpus=NUM_WUMPUS, num_gold=NUM_GOLD):
    starts = list(starts or [(START_R, START_C)])

    # Cada célula é um conjunto de tokens: "P"=poço, "O"=ouro, "B"=morcego.
    celulas = [[set() for _ in range(TAM)] for _ in range(TAM)]

    # Zona segura inicial: célula de saída e vizinhos ortogonais.
    # Nenhum perigo (poço, wumpus, morcego) pode nascer aqui.
    safe_start_zone = set(starts)
    for start_r, start_c in starts:
        for dr, dc in DIRS:
            nr, nc = start_r + dr, start_c + dc
            if 0 <= nr < TAM and 0 <= nc < TAM:
                safe_start_zone.add((nr, nc))

    def perto_start(r, c):
        # Impede que wumpus apareca imediatamente ao lado de qualquer saída.
        return any(max(abs(r - sr), abs(c - sc)) <= 1 for sr, sc in starts)

    todas = [(r, c) for r in range(TAM) for c in range(TAM)
             if (r, c) not in starts]
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
    if len(cand_w) < num_wumpus:
        cand_w = [p for p in todas if p not in pits and p not in safe_start_zone]
    random.shuffle(cand_w)
    wumpus_list = cand_w[:num_wumpus]

    # Ouro não pode compartilhar célula com poço, wumpus ou zona segura inicial.
    used_w = set(wumpus_list)
    cand_o = [p for p in todas if p not in pits and p not in used_w and p not in safe_start_zone]
    random.shuffle(cand_o)
    gold_pos = set()
    for i in range(min(num_gold, len(cand_o))):
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
        self.gold_target = NUM_GOLD
        self.start_pos = (START_R, START_C)
        self.exit_cells = {self.start_pos}
        self.reset()

    # Reinicia o jogo com um novo mundo aleatório, resetando todas as variáveis de estado.
    def reset(self):
        self.celulas, self.wumpuses = criar_mundo(starts=[self.start_pos], num_wumpus=NUM_WUMPUS)
        self.wumpus_vivo = [True] * len(self.wumpuses)
        self.r         = START_R
        self.c         = START_C
        self.dir       = START_DIR
        self.vivo      = True
        self.saiu      = False
        self.score     = 0
        self.ouro      = 0
        self.collected_gold_positions = set()
        self.flecha    = True   # O agente começa com uma única flecha.
        self.visitados = set()  # Células já visitadas (reveladas no mapa).
        self.perc_map  = {}     # Percepções salvas por célula visitada.
        self.msg       = ("", COL_TEXT)
        self._grito    = False
        self.impacto   = False
        self._visitar(START_R, START_C)

    @property
    def blocked_cells(self):
        return set()

    @property
    def game_over(self):
        return (not self.vivo) and (not self.saiu)

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
            self.collected_gold_positions.add((self.r, self.c))
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
        if (self.r, self.c) == self.start_pos:
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


class JogoAjudante:
    def __init__(self):
        self.is_helper_mode = True
        self.gold_target = HELPER_GOLD
        self.exit_cells = {HELPER_EXIT}
        self.msg = ("", COL_TEXT)
        self.reset()

    def reset(self):
        self.celulas, self.wumpuses = criar_mundo(
            starts=HELPER_STARTS,
            num_wumpus=HELPER_WUMPUS,
            num_gold=self.gold_target,
        )
        self.wumpus_vivo = [True] * len(self.wumpuses)
        self.score = 0
        self.ouro = 0
        self.collected_gold_positions = set()
        self.visitados = set()
        self.perc_map = {}
        self.known_pits = set()
        self.known_wumpus = set()
        self.msg = ("", COL_TEXT)
        self.agents = []
        for idx, (pos, dire) in enumerate(zip(HELPER_STARTS, HELPER_DIRS), start=1):
            self.agents.append({
                "nome": f"Heroi {idx}",
                "start": pos,
                "r": pos[0],
                "c": pos[1],
                "dir": dire,
                "vivo": True,
                "saiu": False,
                "ouro": 0,
                "flecha": True,
                "impacto": False,
                "grito": False,
            })
            self._visitar(*pos)

    @property
    def vivo(self):
        return any(a["vivo"] and not a["saiu"] for a in self.agents)

    @property
    def saiu(self):
        vivos = [a for a in self.agents if a["vivo"]]
        return self.ouro >= self.gold_target and vivos and all(a["saiu"] for a in vivos)

    @property
    def game_over(self):
        return (not self.saiu) and (not any(a["vivo"] and not a["saiu"] for a in self.agents))

    def blocked_cells_for(self, idx):
        blocked = set(self.known_pits)
        blocked.update(
            (wr, wc)
            for i, (wr, wc) in enumerate(self.wumpuses)
            if self.wumpus_vivo[i] and (wr, wc) in self.known_wumpus
        )
        for other_idx, agent in enumerate(self.agents):
            if other_idx == idx or not agent["vivo"] or agent["saiu"]:
                continue
            blocked.add((agent["r"], agent["c"]))
        return blocked

    def _remember_pit(self, pos):
        self.known_pits.add(pos)

    def _remember_wumpus(self, pos):
        self.known_wumpus.add(pos)

    def _forget_wumpus(self, pos):
        self.known_wumpus.discard(pos)

    def _reward_survivor_arrow(self, dead_idx):
        gained = []
        for idx, agent in enumerate(self.agents):
            if idx == dead_idx or not agent["vivo"] or agent["saiu"]:
                continue
            if not agent["flecha"]:
                agent["flecha"] = True
                gained.append(agent["nome"])
        if gained:
            self._msg(f"{', '.join(gained)} recebeu uma flecha extra.", COL_OK)

    def _neighbors(self, r, c):
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < TAM and 0 <= nc < TAM:
                yield nr, nc

    def _msg(self, texto, cor=COL_TEXT):
        self.msg = (texto, cor)

    def _visitar(self, r, c):
        self.visitados.add((r, c))
        self.perc_map[(r, c)] = self._perceber(r, c)

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

    def perceber_atual(self, idx):
        agent = self.agents[idx]
        p = set(self._perceber(agent["r"], agent["c"]))
        if agent["impacto"]:
            p.add("Impacto")
        if agent["grito"]:
            p.add("Grito")
        return p

    def _custo(self, idx, extra=0):
        agent = self.agents[idx]
        self.score += C_ACAO + extra
        agent["impacto"] = False
        agent["grito"] = False

    def _agent_alive(self, idx):
        agent = self.agents[idx]
        return agent["vivo"] and not agent["saiu"]

    def _turn_right(self, idx):
        if not self._agent_alive(idx):
            return
        self._custo(idx)
        self.agents[idx]["dir"] = (self.agents[idx]["dir"] + 1) % 4

    def _turn_left(self, idx):
        if not self._agent_alive(idx):
            return
        self._custo(idx)
        self.agents[idx]["dir"] = (self.agents[idx]["dir"] - 1) % 4

    def _pick(self, idx):
        if not self._agent_alive(idx):
            return None
        agent = self.agents[idx]
        self._custo(idx)
        if "O" in self.celulas[agent["r"]][agent["c"]]:
            self.celulas[agent["r"]][agent["c"]].discard("O")
            self.collected_gold_positions.add((agent["r"], agent["c"]))
            self.ouro += 1
            agent["ouro"] += 1
            self.score += R_OURO_AJUDANTE
            self.perc_map[(agent["r"], agent["c"])] = self._perceber(agent["r"], agent["c"])
            return f"{agent['nome']} coletou ouro! +{R_OURO_AJUDANTE}"
        return f"{agent['nome']}: nada para pegar aqui."

    def _shoot(self, idx):
        if not self._agent_alive(idx):
            return None
        agent = self.agents[idx]
        if not agent["flecha"]:
            return f"{agent['nome']} esta sem flecha!"
        self._custo(idx, extra=C_FLECHA)
        agent["flecha"] = False
        dr, dc = DIRS[agent["dir"]]
        r, c = agent["r"] + dr, agent["c"] + dc
        while 0 <= r < TAM and 0 <= c < TAM:
            for i, (wr, wc) in enumerate(self.wumpuses):
                if (wr, wc) == (r, c) and self.wumpus_vivo[i]:
                    self.wumpus_vivo[i] = False
                    self._forget_wumpus((wr, wc))
                    agent["grito"] = True
                    for dr2, dc2 in DIRS:
                        nr2, nc2 = wr + dr2, wc + dc2
                        if (nr2, nc2) in self.visitados:
                            self.perc_map[(nr2, nc2)] = self._perceber(nr2, nc2)
                    return f"{agent['nome']} derrubou um Wumpus!"
            r, c = r + dr, c + dc
        return f"{agent['nome']} errou a flecha."

    def _climb(self, idx):
        if not self._agent_alive(idx):
            return None
        agent = self.agents[idx]
        self._custo(idx)
        if (agent["r"], agent["c"]) == HELPER_EXIT:
            agent["saiu"] = True
            if self.saiu:
                return f"{agent['nome']} saiu e a dupla concluiu a missao!"
            return f"{agent['nome']} chegou a saida compartilhada."
        return f"{agent['nome']} so pode sair pela base do Heroi 1."

    def _check_sala(self, idx):
        agent = self.agents[idx]
        r, c = agent["r"], agent["c"]
        if "B" in self.celulas[r][c]:
            self._bat_teleport(idx, r, c)
            return
        if "P" in self.celulas[r][c]:
            self._remember_pit((r, c))
            agent["vivo"] = False
            self.score += C_MORTE
            self._reward_survivor_arrow(idx)
            self._msg(f"{agent['nome']} caiu num poco! -1000", COL_WARN)
            return
        for i, (wr, wc) in enumerate(self.wumpuses):
            if (wr, wc) == (r, c) and self.wumpus_vivo[i]:
                self._remember_wumpus((r, c))
                agent["vivo"] = False
                self.score += C_MORTE
                self._reward_survivor_arrow(idx)
                self._msg(f"{agent['nome']} foi devorado pelo Wumpus! -1000", COL_WARN)
                return

    def _bat_teleport(self, idx, bat_r, bat_c, depth=0):
        if depth > 5:
            return
        agent = self.agents[idx]
        dest_r, dest_c = agent["r"], agent["c"]
        for _ in range(30):
            cand_r = random.randint(0, TAM - 1)
            cand_c = random.randint(0, TAM - 1)
            occupied = any(
                other_idx != idx and other["vivo"] and (other["r"], other["c"]) == (cand_r, cand_c)
                and (cand_r, cand_c) not in self.exit_cells
                for other_idx, other in enumerate(self.agents)
            )
            if not occupied:
                dest_r, dest_c = cand_r, cand_c
                break
        agent["r"], agent["c"] = dest_r, dest_c
        self._visitar(dest_r, dest_c)
        if depth == 0:
            self._msg(f"{agent['nome']} foi carregado por um morcego!", COL_MORCEGO)
        if "B" in self.celulas[dest_r][dest_c] and (dest_r, dest_c) != (bat_r, bat_c):
            self._bat_teleport(idx, dest_r, dest_c, depth + 1)
            return
        if "P" in self.celulas[dest_r][dest_c]:
            self._remember_pit((dest_r, dest_c))
            agent["vivo"] = False
            self.score += C_MORTE
            self._reward_survivor_arrow(idx)
            self._msg(f"{agent['nome']} caiu em um poco apos o teleporte! -1000", COL_WARN)
            return
        for i, (wr, wc) in enumerate(self.wumpuses):
            if (wr, wc) == (dest_r, dest_c) and self.wumpus_vivo[i]:
                self._remember_wumpus((dest_r, dest_c))
                agent["vivo"] = False
                self.score += C_MORTE
                self._reward_survivor_arrow(idx)
                self._msg(f"{agent['nome']} caiu no Wumpus apos o teleporte! -1000", COL_WARN)
                return

    def apply_actions(self, actions):
        texts = []

        for idx in range(len(self.agents)):
            if actions.get(idx) == "R":
                self._turn_right(idx)
            elif actions.get(idx) == "L":
                self._turn_left(idx)

        for idx in range(len(self.agents)):
            if actions.get(idx) == "F":
                text = self._shoot(idx)
                if text:
                    texts.append(text)

        move_texts = self._apply_moves(actions)
        texts.extend(move_texts)

        for idx in range(len(self.agents)):
            action = actions.get(idx)
            if action == "G":
                text = self._pick(idx)
                if text:
                    texts.append(text)
            elif action == "E":
                text = self._climb(idx)
                if text:
                    texts.append(text)

        if self.saiu:
            texts.append(f"Missao concluida! {self.ouro} ouros coletados pela dupla.")
            self._msg(" | ".join(texts), COL_OK)
        elif texts:
            self._msg(" | ".join(texts), COL_TEXT)

    def _apply_moves(self, actions):
        move_targets = {}
        move_msgs = []

        for idx, agent in enumerate(self.agents):
            if actions.get(idx) != "M" or not self._agent_alive(idx):
                continue
            self._custo(idx)
            dr, dc = DIRS[agent["dir"]]
            nr, nc = agent["r"] + dr, agent["c"] + dc
            if not (0 <= nr < TAM and 0 <= nc < TAM):
                agent["impacto"] = True
                move_msgs.append(f"{agent['nome']} bateu na parede.")
                continue
            move_targets[idx] = (nr, nc)

        if len(move_targets) == 2:
            idxs = list(move_targets.keys())
            i0, i1 = idxs[0], idxs[1]
            if move_targets[i0] == move_targets[i1] and move_targets[i0] not in self.exit_cells:
                shared_target = move_targets[i0]
                roll_0 = random.randint(0, 10)
                roll_1 = random.randint(0, 10)
                while roll_0 == roll_1:
                    roll_0 = random.randint(0, 10)
                    roll_1 = random.randint(0, 10)
                winner = i0 if roll_0 > roll_1 else i1
                loser = i1 if winner == i0 else i0
                loser_fallback = self._resolve_loser_target(loser, shared_target, move_targets, actions)
                move_targets[winner] = shared_target
                if loser_fallback is None:
                    move_targets.pop(loser, None)
                    self.agents[loser]["impacto"] = True
                    move_msgs.append(
                        f"Empate no bloco [{shared_target[0] + 1},{shared_target[1] + 1}]: "
                        f"{self.agents[winner]['nome']} venceu {max(roll_0, roll_1)} a {min(roll_0, roll_1)} e {self.agents[loser]['nome']} ficou sem rota."
                    )
                else:
                    move_targets[loser] = loser_fallback
                    move_msgs.append(
                        f"Empate no bloco [{shared_target[0] + 1},{shared_target[1] + 1}]: "
                        f"{self.agents[winner]['nome']} venceu {max(roll_0, roll_1)} a {min(roll_0, roll_1)} e "
                        f"{self.agents[loser]['nome']} desviou para [{loser_fallback[0] + 1},{loser_fallback[1] + 1}]."
                    )

        for idx, target in list(move_targets.items()):
            for other_idx, other in enumerate(self.agents):
                if idx == other_idx or not other["vivo"]:
                    continue
                other_will_move = other_idx in move_targets
                occupied_end = move_targets.get(other_idx, (other["r"], other["c"])) if other_will_move else (other["r"], other["c"])
                if occupied_end == target and target not in self.exit_cells:
                    move_msgs.append(f"{self.agents[idx]['nome']} nao pode entrar no bloco de {other['nome']}.")
                    move_targets.pop(idx, None)
                    break

        for idx, target in move_targets.items():
            self.agents[idx]["r"], self.agents[idx]["c"] = target
            self._visitar(*target)

        for idx in list(move_targets.keys()):
            self._check_sala(idx)

        return move_msgs

    def _resolve_loser_target(self, loser_idx, blocked_target, move_targets, actions):
        agent = self.agents[loser_idx]
        occupied_now = {
            (other["r"], other["c"])
            for other_idx, other in enumerate(self.agents)
            if other_idx != loser_idx and other["vivo"] and not other["saiu"]
        }
        occupied_future = {
            target
            for other_idx, target in move_targets.items()
            if other_idx != loser_idx
        }

        candidates = []
        for nr, nc in self._neighbors(agent["r"], agent["c"]):
            pos = (nr, nc)
            if pos == blocked_target:
                continue
            if pos in occupied_now and pos not in self.exit_cells:
                continue
            if pos in occupied_future and pos not in self.exit_cells:
                continue
            if pos in self.exit_cells or pos in self.visitados:
                score = 0
            else:
                score = 3
            score += abs(nr - blocked_target[0]) + abs(nc - blocked_target[1])
            if pos in self.exit_cells:
                score -= 2
            candidates.append((score, pos))

        if not candidates:
            return None

        candidates.sort(key=lambda item: (item[0], item[1][0], item[1][1]))
        return candidates[0][1]


class AgentProxy:
    def __init__(self, game, idx):
        self.game = game
        self.idx = idx

    @property
    def r(self):
        return self.game.agents[self.idx]["r"]

    @property
    def c(self):
        return self.game.agents[self.idx]["c"]

    @property
    def dir(self):
        return self.game.agents[self.idx]["dir"]

    @property
    def vivo(self):
        return self.game.agents[self.idx]["vivo"]

    @property
    def saiu(self):
        return self.game.agents[self.idx]["saiu"]

    @property
    def flecha(self):
        return self.game.agents[self.idx]["flecha"]

    @property
    def ouro(self):
        return self.game.ouro

    @property
    def celulas(self):
        return self.game.celulas

    @property
    def visitados(self):
        return self.game.visitados

    @property
    def perc_map(self):
        return self.game.perc_map

    @property
    def wumpuses(self):
        return self.game.wumpuses

    @property
    def wumpus_vivo(self):
        return self.game.wumpus_vivo

    @property
    def gold_target(self):
        return self.game.gold_target

    @property
    def start_pos(self):
        return next(iter(self.game.exit_cells))

    @property
    def exit_cells(self):
        return self.game.exit_cells

    @property
    def blocked_cells(self):
        return self.game.blocked_cells_for(self.idx)

    def perceber_atual(self):
        return self.game.perceber_atual(self.idx)

    def mover(self):
        self.game.apply_actions({self.idx: "M"})

    def virar_direita(self):
        self.game.apply_actions({self.idx: "R"})

    def virar_esquerda(self):
        self.game.apply_actions({self.idx: "L"})

    def pegar(self):
        self.game.apply_actions({self.idx: "G"})

    def atirar(self):
        self.game.apply_actions({self.idx: "F"})

    def subir(self):
        self.game.apply_actions({self.idx: "E"})


class AutoPlayer:
    # IA simples baseada em risco: explora fronteira conhecida, coleta ouro e tenta voltar para sair.
    def __init__(self, jogo, tie_bias="right"):
        self.jogo = jogo
        self.tie_bias = tie_bias
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
        blocked = set(getattr(self.jogo, "blocked_cells", set()))
        blocked.discard(start)
        if goal in getattr(self.jogo, "exit_cells", set()):
            blocked.discard(goal)
        allowed = {cell for cell in allowed if cell not in blocked or cell == goal}
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
        if right == left:
            return (["R"] * right) if self.tie_bias == "right" else (["L"] * left)
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
        if self.jogo.ouro >= self.jogo.gold_target:
            if (r, c) == self.jogo.start_pos:
                self.queue.append("E")
                self.stuck_count = 0
                return
            back = self._path((r, c), self.jogo.start_pos, set(self.jogo.visitados))
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
            if (r, c) == self.jogo.start_pos:
                self.queue.append("E")
                self.stuck_count = 0
                return
            back = self._path((r, c), self.jogo.start_pos, visited)
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
        if (r, c) != self.jogo.start_pos:
            back = self._path((r, c), self.jogo.start_pos, visited)
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

    def next_action(self):
        if not self.jogo.vivo or self.jogo.saiu:
            return None

        # Interrompe qualquer plano para pegar ouro imediatamente ao entrar na célula.
        if "O" in self.jogo.celulas[self.jogo.r][self.jogo.c]:
            self.queue.clear()
            return "G"

        if not self.queue:
            self._enqueue_plan()

        if not self.queue:
            return None

        return self.queue.popleft()

    def _apply_action(self, action):
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

    def step(self):
        action = self.next_action()
        if not action:
            return
        self._apply_action(action)


single_game = Jogo()
helper_game = JogoAjudante()

jogo = single_game
auto_player = AutoPlayer(single_game)
helper_auto_players = [
    AutoPlayer(AgentProxy(helper_game, 0), tie_bias="right"),
    AutoPlayer(AgentProxy(helper_game, 1), tie_bias="left"),
]

MODE_MENU = "menu"
MODE_AUTO = "auto"
MODE_TEST = "test"
MODE_HELPER = "helper"

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


def _draw_collected_gold_marker(surf, rx, ry):
    marker_w = TILE - 42
    marker_h = TILE - 42
    px = rx + (TILE - marker_w) // 2
    py = ry + (TILE - marker_h) // 2

    if img_gold:
        gold_icon = pygame.transform.smoothscale(img_gold, (marker_w, marker_h))
        surf.blit(gold_icon, (px, py))
    else:
        pygame.draw.ellipse(surf, COL_GOLD, (px, py, marker_w, marker_h))
        pygame.draw.ellipse(surf, (210, 160, 0), (px, py, marker_w, marker_h), 2)

    # Check verde centralizado, no mesmo bloco visual do ouro coletado.
    cx = rx + TILE // 2
    cy = ry + TILE // 2
    c1 = (cx - 16, cy + 2)
    c2 = (cx - 6,  cy + 12)
    c3 = (cx + 14, cy - 12)
    pygame.draw.line(surf, COL_OK, c1, c2, 5)
    pygame.draw.line(surf, COL_OK, c2, c3, 5)


def _draw_agent(surf, rx, ry, dire, size=None, area_size=None):
    size = size or SZA
    area_w, area_h = area_size or (TILE, TILE)
    agent_img = img_agent
    if img_agent and size != SZA:
        agent_img = pygame.transform.smoothscale(img_agent, size)
    if agent_img:
        if dire == 3:
            # Esquerda: usa exatamente a PNG original.
            rot = agent_img
        elif dire == 1:
            # Direita: usa a versao espelhada da PNG.
            rot = pygame.transform.flip(agent_img, True, False)
        elif dire == 0:
            # Cima.
            rot = pygame.transform.rotate(agent_img, -90)
        else:
            # Baixo.
            rot = pygame.transform.rotate(agent_img, 90)
        ax    = rx + (area_w - rot.get_width())  // 2
        ay    = ry + (area_h - rot.get_height()) // 2
        surf.blit(rot, (ax, ay))
    else:
        base   = min(area_w, area_h)
        cx, cy = rx + area_w // 2, ry + area_h // 2
        sz     = base // 3
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
    reveal_all = getattr(jogo, "game_over", (not jogo.vivo or jogo.saiu)) or jogo.saiu
    visible    = (r, c) in jogo.visitados or reveal_all

    bg = COL_VISIBLE if visible else COL_HIDDEN
    pygame.draw.rect(surf, bg, (rx, ry, TILE, TILE))

    if (r, c) in getattr(jogo, "exit_cells", {(START_R, START_C)}):
        pygame.draw.rect(surf, COL_START, (rx + 1, ry + 1, TILE - 2, TILE - 2), 3)
        lbl = font_small.render("SAIDA", True, (140, 120, 0))
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

    if reveal_all and (r, c) in getattr(jogo, "collected_gold_positions", set()):
        _draw_collected_gold_marker(surf, rx, ry)

    if getattr(jogo, "is_helper_mode", False):
        here = []
        for idx, agent in enumerate(jogo.agents, start=1):
            if (agent["r"], agent["c"]) == (r, c):
                here.append((idx, agent))
        if here:
            slots = [(rx + 8, ry + 18), (rx + TILE // 2 + 2, ry + 18)]
            for slot_idx, (hero_idx, agent) in enumerate(here[:2]):
                if agent["vivo"]:
                    mini = pygame.Surface((TILE // 2 - 10, TILE - 34), pygame.SRCALPHA)
                    _draw_agent(
                        mini,
                        0,
                        0,
                        agent["dir"],
                        size=(TILE // 2 - 22, TILE // 2 - 22),
                        area_size=(mini.get_width(), mini.get_height()),
                    )
                    surf.blit(mini, slots[slot_idx])
                else:
                    sx, sy = slots[slot_idx]
                    pygame.draw.line(surf, COL_WARN, (sx + 6, sy + 6), (sx + 34, sy + 52), 3)
                    pygame.draw.line(surf, COL_WARN, (sx + 34, sy + 6), (sx + 6, sy + 52), 3)
                tag = font_small.render(str(hero_idx), True, COL_TEXT)
                surf.blit(tag, (slots[slot_idx][0] + 2, slots[slot_idx][1] - 10))
    else:
        is_here = (r == jogo.r and c == jogo.c)
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
    line(f"Ouro: {jogo.ouro} / {jogo.gold_target}")
    if getattr(jogo, "is_helper_mode", False):
        line(f"Valor do ouro: +{R_OURO_AJUDANTE}", COL_GOLD)
        line(f"Wumpus vivos: {sum(1 for x in jogo.wumpus_vivo if x)}")
        sep()
        for idx, agent in enumerate(jogo.agents):
            status = "SAIU" if agent["saiu"] else "VIVO" if agent["vivo"] else "MORTO"
            cor = COL_OK if agent["saiu"] else COL_TEXT if agent["vivo"] else COL_WARN
            row_d = TAM - agent["r"]
            col_d = agent["c"] + 1
            line(agent["nome"], cor, font_bold)
            line(f"Status: {status}", cor)
            line(f"Base: [{TAM - agent['start'][0]},{agent['start'][1] + 1}]")
            line(f"Posicao: [{row_d},{col_d}]")
            line(f"Direcao: {DIR_ARROW[agent['dir']]} {DIR_NAMES[agent['dir']]}")
            line(f"Flecha: {'SIM' if agent['flecha'] else 'NAO'}",
                 COL_OK if agent["flecha"] else COL_WARN)
            if agent["vivo"]:
                percs = jogo.perceber_atual(idx)
                if percs:
                    line("Percepcoes:", COL_TEXT)
                    for p in sorted(percs):
                        icon = PERC_ICON.get(p, "?")
                        line(f"  {icon} {p}", PERC_COR.get(p, COL_TEXT))
            sep()
        line("MODO AJUDANTE", COL_OK, font_bold)
        line("2 computadores agem ao mesmo tempo", COL_TEXT)
        line("ENTER: pausar/continuar", COL_TEXT)
        line("R: reiniciar", COL_TEXT)
        line("ESC: menu", COL_TEXT)
        state = "PAUSADO" if auto_pausado else "RODANDO"
        line(f"Estado: {state}", COL_WARN if auto_pausado else COL_OK)
    else:
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

    if getattr(jogo, "game_over", not jogo.vivo) or jogo.saiu:
        ov = pygame.Surface((TAM * TILE, H_SCR), pygame.SRCALPHA)
        ov.fill((180, 0, 0, 90) if getattr(jogo, "game_over", not jogo.vivo) else (0, 150, 0, 90))
        surf.blit(ov, (0, 0))
        if getattr(jogo, "game_over", not jogo.vivo):
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
    rect_auto = pygame.Rect(bx, 180, bw, bh)
    rect_test = pygame.Rect(bx, 290, bw, bh)
    rect_helper = pygame.Rect(bx, 400, bw, bh)

    pygame.draw.rect(surf, (40, 120, 70), rect_auto, border_radius=10)
    pygame.draw.rect(surf, (70, 90, 150), rect_test, border_radius=10)
    pygame.draw.rect(surf, (150, 95, 40), rect_helper, border_radius=10)

    t1 = font_bold.render("Jogo normal (computador joga)", True, COL_TEXT)
    t2 = font_bold.render("Testar (jogar manual)", True, COL_TEXT)
    t3 = font_bold.render("Modo ajudante (2 computadores)", True, COL_TEXT)
    surf.blit(t1, (rect_auto.centerx - t1.get_width() // 2,
                   rect_auto.centery - t1.get_height() // 2))
    surf.blit(t2, (rect_test.centerx - t2.get_width() // 2,
                   rect_test.centery - t2.get_height() // 2))
    surf.blit(t3, (rect_helper.centerx - t3.get_width() // 2,
                   rect_helper.centery - t3.get_height() // 2))

    hint = font_small.render("Clique em um modo ou use teclas 1, 2 e 3", True, (190, 190, 190))
    surf.blit(hint, (W_SCR // 2 - hint.get_width() // 2, 515))

    pygame.display.flip()
    return rect_auto, rect_test, rect_helper


def get_ingame_menu_button_rect():
    bw, bh = 118, 36
    margin = 10
    return pygame.Rect(W_SCR - bw - margin, H_SCR - bh - margin, bw, bh)


def draw_ingame_menu_button(surf):
    rect = get_ingame_menu_button_rect()
    mouse_pos = pygame.mouse.get_pos()
    hovered = rect.collidepoint(mouse_pos)
    bg = (186, 74, 56) if hovered else (156, 54, 36)
    border = (255, 210, 180) if hovered else (240, 170, 130)
    pygame.draw.rect(surf, bg, rect, border_radius=9)
    pygame.draw.rect(surf, border, rect, 2, border_radius=9)
    lbl = font_bold.render("MENU", True, COL_TEXT)
    surf.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                    rect.centery - lbl.get_height() // 2))
    return rect


def desenhar(jogo):
    tela.fill(COL_HIDDEN)
    for r in range(TAM):
        for c in range(TAM):
            draw_cell(tela, jogo, r, c)
    draw_panel(tela, jogo)
    draw_ingame_menu_button(tela)
    pygame.display.flip()


# Loop principal: captura teclas, executa ação no jogo e redesenha a tela a 60 FPS.
clock = pygame.time.Clock()
while True:
    rect_auto = None
    rect_test = None
    rect_helper = None
    if modo_atual == MODE_MENU:
        rect_auto, rect_test, rect_helper = draw_menu(tela)

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if modo_atual == MODE_MENU:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_1:
                    jogo = single_game
                    jogo.reset()
                    auto_player.reset()
                    auto_pausado = False
                    modo_atual = MODE_AUTO
                    last_auto_tick = pygame.time.get_ticks()
                elif ev.key == pygame.K_2:
                    jogo = single_game
                    jogo.reset()
                    auto_player.reset()
                    auto_pausado = False
                    modo_atual = MODE_TEST
                elif ev.key == pygame.K_3:
                    jogo = helper_game
                    jogo.reset()
                    for player in helper_auto_players:
                        player.reset()
                    auto_pausado = False
                    modo_atual = MODE_HELPER
                    last_auto_tick = pygame.time.get_ticks()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if rect_auto and rect_auto.collidepoint(ev.pos):
                    jogo = single_game
                    jogo.reset()
                    auto_player.reset()
                    auto_pausado = False
                    modo_atual = MODE_AUTO
                    last_auto_tick = pygame.time.get_ticks()
                elif rect_test and rect_test.collidepoint(ev.pos):
                    jogo = single_game
                    jogo.reset()
                    auto_player.reset()
                    auto_pausado = False
                    modo_atual = MODE_TEST
                elif rect_helper and rect_helper.collidepoint(ev.pos):
                    jogo = helper_game
                    jogo.reset()
                    for player in helper_auto_players:
                        player.reset()
                    auto_pausado = False
                    modo_atual = MODE_HELPER
                    last_auto_tick = pygame.time.get_ticks()
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
                elif k == pygame.K_ESCAPE:
                    modo_atual = MODE_MENU
            elif modo_atual == MODE_HELPER:
                if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    auto_pausado = not auto_pausado
                    jogo._msg("Modo ajudante pausado." if auto_pausado else "Modo ajudante retomado.", COL_OK)
                elif k == pygame.K_r:
                    jogo.reset()
                    for player in helper_auto_players:
                        player.reset()
                    auto_pausado = False
                elif k == pygame.K_ESCAPE:
                    modo_atual = MODE_MENU
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if modo_atual in (MODE_TEST, MODE_AUTO, MODE_HELPER):
                if get_ingame_menu_button_rect().collidepoint(ev.pos):
                    auto_pausado = False
                    modo_atual = MODE_MENU

    if modo_atual == MODE_AUTO and (not auto_pausado) and jogo.vivo and not jogo.saiu:
        now = pygame.time.get_ticks()
        if now - last_auto_tick >= AUTO_DELAY_MS:
            auto_player.step()
            last_auto_tick = now

    if modo_atual == MODE_HELPER and (not auto_pausado) and jogo.vivo and not jogo.saiu:
        now = pygame.time.get_ticks()
        if now - last_auto_tick >= AUTO_DELAY_MS:
            actions = {}
            for idx, player in enumerate(helper_auto_players):
                action = player.next_action()
                if action:
                    actions[idx] = action
            if actions:
                jogo.apply_actions(actions)
            last_auto_tick = now

    if modo_atual != MODE_MENU:
        desenhar(jogo)

    clock.tick(60)
