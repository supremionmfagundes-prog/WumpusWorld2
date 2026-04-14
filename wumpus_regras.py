import os
import random
import sys
import pygame

pygame.init()

# CONFIGURAÇÕES
TAM = 6
TILE = 90
LARGURA = TAM * TILE
ALTURA = TAM * TILE + 140
FPS = 30
START_POS = (0, 0)

# CUSTOS E RECOMPENSAS
COST_ACTION = -1
COST_SHOOT = -10
REWARD_GOLD = 1000
REWARD_PIT = -1000
REWARD_WUMPUS = -1000

# CORES
GRAMA = (106, 170, 100)
GRAMA_ESCURA = (60, 120, 65)
PRETO = (0, 0, 0)
BRANCO = (240, 240, 240)
VERMELHO = (200, 50, 50)
AMARELO = (255, 215, 0)
AZUL = (50, 100, 255)
CIANO = (140, 220, 255)
ROXO = (130, 80, 180)

Tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Mundo do Wumpus")
fonte = pygame.font.SysFont("Arial", 20)
fonte_titulo = pygame.font.SysFont("Arial", 24, bold=True)

img_pit = None
img_wumpus = None
img_gold = None
img_agent = None
img_bat = None


def carregar_imagem(nome, size):
    caminho = os.path.join(os.path.dirname(__file__), nome)
    if os.path.exists(caminho):
        try:
            imagem = pygame.image.load(caminho).convert_alpha()
            return pygame.transform.scale(imagem, size)
        except Exception:
            return None
    return None


img_pit = carregar_imagem("pit.png", (TILE - 20, TILE - 20))
img_wumpus = carregar_imagem("wumpus.png", (TILE - 20, TILE - 20))
img_gold = carregar_imagem("gold.png", (TILE - 24, TILE - 24))
img_agent = carregar_imagem("agent.png", (TILE - 30, TILE - 30))
img_bat = carregar_imagem("bat.png", (TILE - 20, TILE - 20))


def criar_mundo():
    todas_posicoes = [(i, j) for i in range(TAM) for j in range(TAM) if (i, j) != START_POS]
    random.shuffle(todas_posicoes)

    mundo = [["" for _ in range(TAM)] for _ in range(TAM)]
    wumpus_pos = todas_posicoes[:2]
    pit_pos = todas_posicoes[2:6]
    gold_pos = todas_posicoes[6:9]
    bat_pos = todas_posicoes[9:11]

    for x, y in pit_pos:
        mundo[x][y] = "P"
    for x, y in wumpus_pos:
        mundo[x][y] = "W"
    for x, y in gold_pos:
        mundo[x][y] = "G"
    for x, y in bat_pos:
        mundo[x][y] = "B"

    return mundo, wumpus_pos, bat_pos


mundo, wumpus_pos, bat_pos = criar_mundo()

agente_x, agente_y = START_POS
facing = 1  # 0 = cima, 1 = direita, 2 = baixo, 3 = esquerda
score = 0
alive = True
won = False
bump = False
scream = False
arrow_count = 1
teleported = False
bat_origin = None


DIRECOES = [(-1, 0), (0, 1), (1, 0), (0, -1)]
DIRECAO_NOME = ["Norte", "Leste", "Sul", "Oeste"]


def posicoes_adjacentes(x, y):
    for dx, dy in DIRECOES:
        nx, ny = x + dx, y + dy
        if 0 <= nx < TAM and 0 <= ny < TAM:
            yield nx, ny


def perceber():
    sensacoes = []
    if bump:
        sensacoes.append("Impacto")

    for nx, ny in posicoes_adjacentes(agente_x, agente_y):
        if mundo[nx][ny] == "P":
            if "Brisa" not in sensacoes:
                sensacoes.append("Brisa")
        if mundo[nx][ny] == "W" and (nx, ny) in wumpus_pos:
            if "Fedor" not in sensacoes:
                sensacoes.append("Fedor")
        if mundo[nx][ny] == "B":
            if "Grito" not in sensacoes:
                sensacoes.append("Grito")

    if mundo[agente_x][agente_y] == "G":
        if "Brilho" not in sensacoes:
            sensacoes.append("Brilho")

    if scream:
        sensacoes.append("Scream")

    return sensacoes


def sortear_teleporte(origem):
    posicoes = [(i, j) for i in range(TAM) for j in range(TAM) if (i, j) != origem]
    return random.choice(posicoes)


def reiniciar():
    global mundo, wumpus_pos, bat_pos, agente_x, agente_y, facing, score, alive, won, bump, scream, arrow_count, teleported, bat_origin
    mundo, wumpus_pos, bat_pos = criar_mundo()
    agente_x, agente_y = START_POS
    facing = 1
    score = 0
    alive = True
    won = False
    bump = False
    scream = False
    arrow_count = 1
    teleported = False
    bat_origin = None


def matar_wumpus(x, y):
    global scream
    if (x, y) in wumpus_pos:
        wumpus_pos.remove((x, y))
        scream = True
        return True
    return False


def mover_para_frente():
    global agente_x, agente_y, bump, score, alive, won, teleported, bat_origin
    if not alive or won:
        return

    dx, dy = DIRECOES[facing]
    nx, ny = agente_x + dx, agente_y + dy
    score += COST_ACTION
    bump = False
    teleported = False
    bat_origin = None

    if nx < 0 or nx >= TAM or ny < 0 or ny >= TAM:
        bump = True
        return

    agente_x, agente_y = nx, ny

    if mundo[agente_x][agente_y] == "P":
        score += REWARD_PIT
        alive = False
        return

    if mundo[agente_x][agente_y] == "W" and (agente_x, agente_y) in wumpus_pos:
        score += REWARD_WUMPUS
        alive = False
        return

    if mundo[agente_x][agente_y] == "B":
        bat_origin = (agente_x, agente_y)
        destino = sortear_teleporte(bat_origin)
        agente_x, agente_y = destino
        teleported = True
        if mundo[agente_x][agente_y] == "P":
            score += REWARD_PIT
            alive = False
        elif mundo[agente_x][agente_y] == "W" and (agente_x, agente_y) in wumpus_pos:
            score += REWARD_WUMPUS
            alive = False
        return


def virar_direita():
    global facing, score, bump
    if not alive or won:
        return
    facing = (facing + 1) % 4
    score += COST_ACTION
    bump = False


def pegar_objeto():
    global score, bump
    if not alive or won:
        return
    score += COST_ACTION
    bump = False
    if mundo[agente_x][agente_y] == "G":
        score += REWARD_GOLD
        mundo[agente_x][agente_y] = ""


def atirar_flecha():
    global score, bump, arrow_count, scream
    if not alive or won:
        return
    score += COST_ACTION + COST_SHOOT
    bump = False
    if arrow_count <= 0:
        return
    arrow_count -= 1

    dx, dy = DIRECOES[facing]
    x, y = agente_x, agente_y
    while True:
        x += dx
        y += dy
        if x < 0 or x >= TAM or y < 0 or y >= TAM:
            break
        if (x, y) in wumpus_pos:
            matar_wumpus(x, y)
            break


def subir():
    global score, won
    if not alive or won:
        return
    score += COST_ACTION
    if (agente_x, agente_y) == START_POS:
        won = True


def desenhar_celula(rect, conteudo, revelar):
    if conteudo == "P":
        if revelar:
            if img_pit:
                Tela.blit(img_pit, (rect.x + 10, rect.y + 10))
            else:
                pygame.draw.circle(Tela, PRETO, rect.center, 22)
    elif conteudo == "W":
        if revelar and (rect.topleft in [((x * TILE), (y * TILE)) for x, y in wumpus_pos]):
            if img_wumpus:
                Tela.blit(img_wumpus, (rect.x + 10, rect.y + 10))
            else:
                pygame.draw.rect(Tela, VERMELHO, rect.inflate(-40, -40))
    elif conteudo == "G":
        if revelar:
            if img_gold:
                Tela.blit(img_gold, (rect.x + 12, rect.y + 12))
            else:
                pygame.draw.circle(Tela, AMARELO, rect.center, 18)
    elif conteudo == "B":
        if revelar:
            if img_bat:
                Tela.blit(img_bat, (rect.x + 10, rect.y + 10))
            else:
                pygame.draw.circle(Tela, ROXO, rect.center, 20)


def desenhar():
    Tela.fill(GRAMA)

    revelar = not alive or won
    for i in range(TAM):
        for j in range(TAM):
            rect = pygame.Rect(j * TILE, i * TILE, TILE, TILE)
            pygame.draw.rect(Tela, PRETO, rect, 2)
            desenhar_celula(rect, mundo[i][j], revelar)

    agente_rect = pygame.Rect(agente_y * TILE, agente_x * TILE, TILE, TILE)
    if alive:
        if img_agent:
            Tela.blit(img_agent, (agente_y * TILE + 15, agente_x * TILE + 15))
        else:
            pygame.draw.rect(Tela, AZUL, agente_rect.inflate(-30, -30))
            dx, dy = DIRECOES[facing]
            pygame.draw.line(Tela, BRANCO, agente_rect.center, (agente_rect.centerx + dy * 20, agente_rect.centery - dx * 20), 4)
    else:
        if mundo[agente_x][agente_y] == "P":
            if img_pit:
                Tela.blit(img_pit, (agente_y * TILE + 10, agente_x * TILE + 10))
            else:
                pygame.draw.circle(Tela, PRETO, agente_rect.center, 22)
        elif mundo[agente_x][agente_y] == "W":
            if img_wumpus:
                Tela.blit(img_wumpus, (agente_y * TILE + 10, agente_x * TILE + 10))
            else:
                pygame.draw.rect(Tela, VERMELHO, agente_rect.inflate(-40, -40))
        elif mundo[agente_x][agente_y] == "B":
            if img_bat:
                Tela.blit(img_bat, (agente_y * TILE + 10, agente_x * TILE + 10))
            else:
                pygame.draw.circle(Tela, ROXO, agente_rect.center, 20)
        pygame.draw.line(Tela, VERMELHO, (agente_rect.left + 10, agente_rect.top + 10), (agente_rect.right - 10, agente_rect.bottom - 10), 5)
        pygame.draw.line(Tela, VERMELHO, (agente_rect.right - 10, agente_rect.top + 10), (agente_rect.left + 10, agente_rect.bottom - 10), 5)

    sensacoes = perceber()
    y_text = LARGURA + 10
    infos = [
        f"Posição: [{agente_x + 1},{agente_y + 1}]",
        f"Direção: {DIRECAO_NOME[facing]}",
        f"Pontuação: {score}",
        f"Flechas: {arrow_count}",
    ]
    for info in infos:
        render = fonte.render(info, True, PRETO)
        Tela.blit(render, (10, y_text))
        y_text += 24

    render = fonte_titulo.render("Sensores:", True, PRETO)
    Tela.blit(render, (10, y_text))
    y_text += 28

    texto = ", ".join(sensacoes) if sensacoes else "Nada"
    render = fonte.render(texto, True, PRETO)
    Tela.blit(render, (10, y_text))
    y_text += 30

    status = "" if alive and not won else ("VENCEU!" if won else "MORREU!")
    if status:
        render = fonte_titulo.render(status, True, VERMELHO if not won else AZUL)
        Tela.blit(render, (10, y_text))
        y_text += 30

    instrucoes = [
        "W = mover para frente",
        "D = virar à direita",
        "G = pegar ouro",
        "F = atirar flecha",
        "C = subir/exit",
        "R = reiniciar",
    ]
    for instrucao in instrucoes:
        render = fonte.render(instrucao, True, PRETO)
        Tela.blit(render, (LARGURA - 260, LARGURA + 10 + 24 * instrucoes.index(instrucao)))

    pygame.display.flip()


clock = pygame.time.Clock()

while True:
    scream = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                mover_para_frente()
            elif event.key == pygame.K_d:
                virar_direita()
            elif event.key == pygame.K_g:
                pegar_objeto()
            elif event.key == pygame.K_f:
                atirar_flecha()
            elif event.key == pygame.K_c:
                subir()
            elif event.key == pygame.K_r:
                reiniciar()

    desenhar()
    clock.tick(FPS)
