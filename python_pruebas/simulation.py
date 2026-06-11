
import pygame
import Box2D
from Box2D import b2World, b2Vec2
import random
import math

# =========================================================================
# CONSTANTES DEL APÉNDICE (Supplementary Table S5, arena "large")
# =========================================================================
N_MAX    = 120
K_ON     = 0.015
K_FORGET = 0.09
K_C      = 1.0
K_OFF    = 0.015
K_ORIENT = 0.7

F0      = 2.8
F_IND   = 10.0 * F0
GAMMA_LIN = 1.48
GAMMA_ROT = 1.44
PHI_MAX   = math.radians(52)

N0 = N_MAX // 5   # umbral Eq. 3: N_att <= N0 → damping máximo

# Geometría arena "large" (Tabla S2, cm)
W_ARENA    = 19.21
SLIT1_X    = 12.92
SLIT2_X    = 19.16
EXIT_SIZE  = 3.69
WALL_THICK = 0.29

# Geometría carga I-Beam "large" (Tabla S2, cm)
L_LONG  = 4.59
L_SHORT = 2.19
L_WIDTH = 0.59
L_STEM  = 9.59

# Renderizado
PPM      = 30.0
DT       = 1.0 / 60.0
SCREEN_W = int(30 * PPM)
SCREEN_H = int(W_ARENA * PPM)

# =========================================================================
# PERÍMETRO EXTERIOR DEL I-BEAM (12 vértices, antihorario)
# =========================================================================
def _ibeam_exterior_verts():
    hw = L_WIDTH / 2
    hs = L_STEM  / 2
    ll = L_LONG  / 2
    ls = L_SHORT / 2
    return [
        (-hs - hw, -ll),   # 0
        (-hs + hw, -ll),   # 1
        (-hs + hw, -hw),   # 2  ← borde interior seg 1→2
        ( hs - hw, -hw),   # 3
        ( hs - hw, -ls),   # 4  ← borde interior seg 3→4
        ( hs + hw, -ls),   # 5
        ( hs + hw,  ls),   # 6
        ( hs - hw,  ls),   # 7
        ( hs - hw,  hw),   # 8  ← borde interior seg 7→8
        (-hs + hw,  hw),   # 9
        (-hs + hw,  ll),   # 10 ← borde interior seg 9→10
        (-hs - hw,  ll),   # 11
    ]

def generate_attachment_sites(spacing=0.3):
    """
    Sitios equiespaciados SOLO en el perímetro EXTERIOR del I-Beam.
    Normal exterior verificada: dot(centro_segmento, normal) > 0.
    """
    verts = _ibeam_exterior_verts()
    n     = len(verts)
    sites = []

    for i in range(n):
        x0, y0 = verts[i]
        x1, y1 = verts[(i + 1) % n]
        dx, dy  = x1 - x0, y1 - y0
        L       = math.hypot(dx, dy)

        # Normal exterior (polígono antihorario → rotar segmento -90°)
        nx, ny = dy / L, -dx / L

        # Verificar que es exterior: el vector desde (0,0) al centro apunta igual que la normal
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if cx * nx + cy * ny < 0.01:
            continue   # borde interior — no poner sitios aquí

        n_pts = max(1, int(L / spacing))
        for k in range(n_pts):
            t  = (k + 0.5) / n_pts
            px = x0 + t * dx
            py = y0 + t * dy
            sites.append({
                'id':        len(sites),
                'local_pos': b2Vec2(px, py),
                'normal':    b2Vec2(nx, ny),
                'state':     'empty',
                'pull_dir':  b2Vec2(nx, ny),
            })

    return sites


# =========================================================================
# DIRECCIÓN OBJETIVO (lógica de tres cámaras, Supplementary Note 1)
# =========================================================================
def target_for_site(world_pos):
    x = world_pos.x
    if x < SLIT1_X:
        return b2Vec2(SLIT1_X, W_ARENA / 2)
    elif x < SLIT2_X:
        return b2Vec2(SLIT2_X, W_ARENA / 2)
    else:
        return b2Vec2(SCREEN_W / PPM + 5, W_ARENA / 2)


def clamp_to_phi_max(desired_local, normal_local):
    """
    Proyecta desired_local dentro de ±PHI_MAX respecto a normal_local.
    Devuelve el b2Vec2 local resultante (unitario).
    """
    na = math.atan2(normal_local.y, normal_local.x)
    da = math.atan2(desired_local.y, desired_local.x)
    diff = (da - na + math.pi) % (2 * math.pi) - math.pi
    diff = max(-PHI_MAX, min(PHI_MAX, diff))
    fa   = na + diff
    return b2Vec2(math.cos(fa), math.sin(fa))


# =========================================================================
# CLASE CARGA
# =========================================================================
class TLoad:
    def __init__(self, world):
        self.body = world.CreateDynamicBody(
            position=(4.0, W_ARENA / 2),
            angle=0.0,
            linearDamping=GAMMA_LIN * N_MAX,
            angularDamping=GAMMA_ROT * N_MAX,
        )
        hw = L_WIDTH / 2
        hs = L_STEM  / 2
        ll = L_LONG  / 2
        ls = L_SHORT / 2

        # Palo central (fixture 0)
        self.body.CreatePolygonFixture(
            box=(hs, hw, (0, 0), 0),
            density=1.0, friction=0.0, restitution=0.0)
        # Travesaño largo (fixture 1)
        self.body.CreatePolygonFixture(
            box=(hw, ll, (-hs, 0), 0),
            density=1.0, friction=0.0, restitution=0.0)
        # Travesaño corto (fixture 2)
        self.body.CreatePolygonFixture(
            box=(hw, ls, ( hs, 0), 0),
            density=1.0, friction=0.0, restitution=0.0)

        self.sites = generate_attachment_sites()


# =========================================================================
# SIMULACIÓN PRINCIPAL
# =========================================================================
def run_simulation():
    random.seed(42)

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("TFG Leire — Réplica Gillespie (Dreyer 2025)")
    clock = pygame.time.Clock()
    font  = pygame.font.SysFont(None, 22)

    world = b2World(gravity=(0, 0))

    # --- Muros ---
    walls = world.CreateStaticBody(position=(0, 0))
    walls.CreatePolygonFixture(box=(40, 0.5, (15, -0.5),          0), friction=0.0, restitution=0.0)
    walls.CreatePolygonFixture(box=(40, 0.5, (15, W_ARENA + 0.5), 0), friction=0.0, restitution=0.0)
    walls.CreatePolygonFixture(box=(0.5, W_ARENA/2, (-0.5,   W_ARENA/2), 0), friction=0.0, restitution=0.0)
    hw_w  = WALL_THICK / 2
    wall_h = (W_ARENA - EXIT_SIZE) / 2
    hw_y  = wall_h / 2
    walls.CreatePolygonFixture(box=(hw_w, hw_y, (SLIT1_X, hw_y),           0), friction=0.0, restitution=0.0)
    walls.CreatePolygonFixture(box=(hw_w, hw_y, (SLIT1_X, W_ARENA - hw_y), 0), friction=0.0, restitution=0.0)
    walls.CreatePolygonFixture(box=(hw_w, hw_y, (SLIT2_X, hw_y),           0), friction=0.0, restitution=0.0)
    walls.CreatePolygonFixture(box=(hw_w, hw_y, (SLIT2_X, W_ARENA - hw_y), 0), friction=0.0, restitution=0.0)

    load = TLoad(world)

    running        = True
    paused         = False
    step_once      = False
    gillespie_time = 0.0
    box2d_time     = 0.0
    STEPS_PER_FRAME = 10

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_RIGHT and paused:
                    step_once = True
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                click  = b2Vec2(mx / PPM, W_ARENA - my / PPM)
                for s in load.sites:
                    wp = load.body.GetWorldPoint(s['local_pos'])
                    if (wp - click).length < 0.8:
                        v_loc = load.body.GetLinearVelocityFromLocalPoint(s['local_pos'])
                        print(f"Sitio {s['id']:3d} | {s['state']:7s} | v_loc={v_loc.length:.3f}")
                        break

        if not paused or step_once:
            step_once = False

            for _ in range(STEPS_PER_FRAME):

                # --- Clasificar sitios ---
                empty_sites = [s for s in load.sites if s['state'] == 'empty']
                info_sites  = [s for s in load.sites if s['state'] == 'info']
                pull_sites  = [s for s in load.sites if s['state'] == 'puller']
                lift_sites  = [s for s in load.sites if s['state'] == 'lifter']
                N_att = len(info_sites) + len(pull_sites) + len(lift_sites)

                # --- Eq. 3: amortiguamiento ---
                if N_att <= N0:
                    load.body.linearDamping  = GAMMA_LIN * N_MAX
                    load.body.angularDamping = GAMMA_ROT * N_MAX
                else:
                    load.body.linearDamping  = GAMMA_LIN * N_att
                    load.body.angularDamping = GAMMA_ROT * N_att

                # =================================================
                # GILLESPIE (Eqs. 4–9)
                # =================================================
                if box2d_time >= gillespie_time:

                    R_att    = K_ON     * len(empty_sites)
                    R_forget = K_FORGET * len(info_sites)
                    R_det    = K_OFF    * (len(pull_sites) + len(lift_sites))
                    R_orient = K_ORIENT * (len(pull_sites) + len(info_sites))

                    # Tasas individuales de cambio de rol (Eq. 1 + Eq. 6)
                    R_c      = 0.0
                    rc_items = []
                    for s in pull_sites + lift_sites:
                        v_loc = load.body.GetLinearVelocityFromLocalPoint(s['local_pos'])
                        f_loc = v_loc * GAMMA_LIN
                        wd    = load.body.GetWorldVector(s['pull_dir'])
                        dot   = wd.dot(f_loc)
                        rate  = K_C * math.exp((dot / F_IND) * (1 if s['state'] == 'lifter' else -1))
                        rc_items.append((s, rate))
                        R_c += rate

                    R_tot = R_att + R_forget + R_c + R_det + R_orient

                    if R_tot > 1e-12:
                        # Tiempo al próximo evento (Eq. 13)
                        delta_t = math.log(1.0 / random.random()) / R_tot
                        gillespie_time += delta_t

                        # Selección del evento (segundo paso)
                        r2 = random.random() * R_tot

                        if r2 < R_att:
                            # ACOPLAMIENTO → nuevo informado
                            s         = random.choice(empty_sites)
                            s['state'] = 'info'
                            wp        = load.body.GetWorldPoint(s['local_pos'])
                            target    = target_for_site(wp)
                            d_world   = target - wp
                            if d_world.length > 0.01:
                                d_world.Normalize()
                                d_local       = load.body.GetLocalVector(d_world)
                                s['pull_dir'] = clamp_to_phi_max(d_local, s['normal'])
                            else:
                                s['pull_dir'] = b2Vec2(s['normal'].x, s['normal'].y)

                        elif r2 < R_att + R_forget:
                            # OLVIDO → informado pasa a no informado (Eq. 14)
                            s     = random.choice(info_sites)
                            v_loc = load.body.GetLinearVelocityFromLocalPoint(s['local_pos'])
                            f_loc = v_loc * GAMMA_LIN
                            wd    = load.body.GetWorldVector(s['pull_dir'])
                            dot   = wd.dot(f_loc)
                            p_pull = 1.0 / (1.0 + math.exp(-2.0 * dot / F_IND))
                            s['state'] = 'puller' if random.random() < p_pull else 'lifter'

                        elif r2 < R_att + R_forget + R_c:
                            # CAMBIO DE ROL
                            r_sel = random.random() * R_c
                            acum  = 0.0
                            for s, rate in rc_items:
                                acum += rate
                                if acum >= r_sel:
                                    s['state'] = 'puller' if s['state'] == 'lifter' else 'lifter'
                                    break

                        elif r2 < R_att + R_forget + R_c + R_det:
                            # DESACOPLAMIENTO
                            s = random.choice(pull_sites + lift_sites)
                            s['state'] = 'empty'

                        else:
                            # REORIENTACIÓN
                            s  = random.choice(pull_sites + info_sites)
                            wp = load.body.GetWorldPoint(s['local_pos'])

                            if s['state'] == 'info':
                                target  = target_for_site(wp)
                                d_world = target - wp
                            else:
                                # Puller: alinea con f_loc (Eq. 2)
                                v_loc   = load.body.GetLinearVelocityFromLocalPoint(s['local_pos'])
                                d_world = b2Vec2(v_loc.x * GAMMA_LIN, v_loc.y * GAMMA_LIN)

                            if d_world.length > 0.01:
                                d_world.Normalize()
                                d_local       = load.body.GetLocalVector(d_world)
                                s['pull_dir'] = clamp_to_phi_max(d_local, s['normal'])

                # =================================================
                # APLICAR FUERZAS (tercer paso)
                # =================================================
                for s in info_sites + pull_sites:
                    wp = load.body.GetWorldPoint(s['local_pos'])
                    wd = load.body.GetWorldVector(s['pull_dir'])
                    load.body.ApplyForce(force=wd * F0, point=wp, wake=True)

                world.Step(DT, 10, 10)
                box2d_time += DT

        # =================================================
        # RENDERIZADO
        # =================================================
        screen.fill((240, 240, 240))

        # Paredes
        for fix in walls.fixtures:
            verts = [(walls.transform * v) * PPM for v in fix.shape.vertices]
            verts = [(int(v[0]), int(SCREEN_H - v[1])) for v in verts]
            pygame.draw.polygon(screen, (100, 100, 100), verts)

        # Carga
        for fix in load.body.fixtures:
            verts = [(load.body.transform * v) * PPM for v in fix.shape.vertices]
            verts = [(int(v[0]), int(SCREEN_H - v[1])) for v in verts]
            pygame.draw.polygon(screen, (200, 50, 50), verts)

        # Sitios de acople + flechas de pull_dir
        col = {'info': (0,0,255), 'puller': (0,200,0), 'lifter': (20,20,20), 'empty': (190,190,190)}
        for s in load.sites:
            wp  = load.body.GetWorldPoint(s['local_pos'])
            px  = int(wp.x * PPM)
            py  = int((W_ARENA - wp.y) * PPM)
            pygame.draw.circle(screen, col[s['state']], (px, py), 3)
            if s['state'] in ('info', 'puller'):
                wd = load.body.GetWorldVector(s['pull_dir'])
                pygame.draw.line(screen, (255,140,0), (px,py),
                                 (int(px + wd.x*10), int(py - wd.y*10)), 1)

        # HUD
        n_i = len(info_sites)
        n_p = len(pull_sites)
        n_l = len(lift_sites)
        hud = [
            f"t_sim={box2d_time:.1f}s  t_gill={gillespie_time:.1f}s",
            f"N_att={N_att}/{N_MAX}  info={n_i}  pull={n_p}  lift={n_l}",
            f"vel={load.body.linearVelocity.length:.3f} cm/s  x={load.body.position.x:.2f}",
            "[SPACE] pausa   [→] paso   [click] info sitio",
        ]
        for i, txt in enumerate(hud):
            screen.blit(font.render(txt, True, (0,0,0)), (8, 8 + i*22))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    run_simulation()