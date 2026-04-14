import pygame
import os

pygame.init()

size = (120, 120)
root = os.path.dirname(__file__)

if not os.path.exists(root):
    os.makedirs(root)


def save(name, draw_func):
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    draw_func(surf)
    pygame.image.save(surf, os.path.join(root, name))
    print(f"Saved {name}")


import pygame.draw as draw

save('pit.png', lambda s: (draw.circle(s, (30, 30, 30), (60, 60), 40),
                           draw.circle(s, (80, 80, 80), (60, 60), 26)))

save('wind.png', lambda s: (draw.circle(s, (180, 220, 255), (60, 60), 45),
                            draw.arc(s, (80, 160, 255), (15, 35, 90, 50), 3.14, 5.0, 8),
                            draw.arc(s, (80, 160, 255), (10, 50, 100, 50), 2.8, 4.6, 8),
                            draw.arc(s, (80, 160, 255), (20, 25, 80, 45), 3.5, 5.2, 6)))

save('gold.png', lambda s: (draw.circle(s, (255, 215, 0), (60, 60), 35),
                            draw.circle(s, (255, 255, 170), (55, 50), 12),
                            draw.circle(s, (255, 255, 180), (65, 55), 10)))

save('agent.png', lambda s: (draw.rect(s, (50, 100, 255), (20, 20, 80, 80), border_radius=20),
                             draw.circle(s, (255, 225, 200), (60, 45), 18),
                             draw.circle(s, (0, 0, 0), (54, 42), 4),
                             draw.circle(s, (0, 0, 0), (66, 42), 4),
                             draw.arc(s, (0, 0, 0), (45, 50, 30, 20), 3.14, 0, 3)))
