import pygame
import Box2D
from Box2D import b2World, b2Vec2
import random
import math

N_MAX    = 120
K_ON     = 0.015
K_FORGET = 0.09
K_C      = 1.0
K_OFF    = 0.015
K_ORIENT = 0.7

F0        = 2.8
F_IND     = 10.0 * F0
GAMMA_LIN = 1.48
GAMMA_ROT = 1.44
PHI_MAX   = math.radians(52)
N0        = N_MAX // 5   

W_ARENA    = 19.21
SLIT1_X    = 12.92
SLIT2_X    = 19.16
EXIT_SIZE  = 3.69
WALL_THICK = 0.29

L_LONG  = 4.59
L_SHORT = 2.19
L_WIDTH = 0.59
L_STEM  = 9.59

PPM      = 30.0
DT       = 1.0 / 60.0
SCREEN_W = int(30 * PPM)
SCREEN_H = int(W_ARENA * PPM)

P_INFORMED_TEST = 1.0  
RANDOM_SEED = 144

def _ibeam_exterior_verts():
    hw, hs, ll, ls = L_WIDTH/2, L_STEM/2, L_LONG/2, L_SHORT/2
    return [
        (-hs - hw, -ll),   (-hs + hw, -ll),   (-hs + hw, -hw),
        ( hs - hw, -hw),   ( hs - hw, -ls),   ( hs + hw, -ls),
        ( hs + hw,  ls),   ( hs - hw,  ls),   ( hs - hw,  hw),
        (-hs + hw,  hw),   (-hs + hw,  ll),   (-hs - hw,  ll)
    ]

def generate_attachment_sites():
    verts = _ibeam_exterior_verts()
    n = len(verts)
    valid_segments = []
    total_length = 0.0
    
    for i in range(n):
        x0, y0 = verts[i]
        x1, y1 = verts[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        nx, ny = dy / L, -dx / L
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if cx * nx + cy * ny >= 0.01:
            valid_segments.append({'x0':x0, 'y0':y0, 'dx':dx, 'dy':dy, 'L':L, 'nx':nx, 'ny':ny})
            total_length += L

    sites = []
    sites_created = 0
    for idx, seg in enumerate(valid_segments):
        if idx == len(valid_segments) - 1:
            n_pts = N_MAX - sites_created 
        else:
            n_pts = int(round(N_MAX * (seg['L'] / total_length)))
        
        for k in range(n_pts):
            t = (k + 0.5) / n_pts if n_pts > 0 else 0.5
            sites.append({
                'id': len(sites),
                'local_pos': b2Vec2(seg['x0'] + t * seg['dx'], seg['y0'] + t * seg['dy']),
                'normal': b2Vec2(seg['nx'], seg['ny']),
                'state': 'empty',
                'pull_dir': b2Vec2(seg['nx'], seg['ny']),
            })
        sites_created += n_pts
        
    assert len(sites) == N_MAX
    return sites

def target_for_site(world_pos):
    x = world_pos.x
    if x < SLIT1_X - 0.5: return b2Vec2(SLIT1_X + 1.0, W_ARENA / 2)
    elif x < SLIT2_X - 0.5: return b2Vec2(SLIT2_X + 1.0, W_ARENA / 2)
    else: return b2Vec2(W_ARENA + 10, W_ARENA / 2)

def clamp_to_phi_max(desired_local, normal_local):
    na = math.atan2(normal_local.y, normal_local.x)
    da = math.atan2(desired_local.y, desired_local.x)
    diff = (da - na + math.pi) % (2 * math.pi) - math.pi
    diff = max(-PHI_MAX, min(PHI_MAX, diff))
    fa = na + diff
    return b2Vec2(math.cos(fa), math.sin(fa))

class TLoad:
    def __init__(self, world):
        self.body = world.CreateDynamicBody(position=(4.0, W_ARENA / 2), angle=0.0, linearDamping=0.0, angularDamping=0.0)
        self.body.bullet = True 
        hw, hs, ll, ls = L_WIDTH / 2, L_STEM / 2, L_LONG / 2, L_SHORT / 2
        self.body.CreatePolygonFixture(box=(hs, hw, (0, 0), 0), density=1.0, friction=0.0, restitution=0.0)
        self.body.CreatePolygonFixture(box=(hw, ll, (-hs, 0), 0), density=1.0, friction=0.0, restitution=0.0)
        self.body.CreatePolygonFixture(box=(hw, ls, ( hs, 0), 0), density=1.0, friction=0.0, restitution=0.0)
        self.sites = generate_attachment_sites()

def run_simulation():
    random.seed(RANDOM_SEED)
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("TFG Leire — Replay Final V1.0")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    world = b2World(gravity=(0, 0))

    walls = world.CreateStaticBody(position=(0, 0))
    walls.CreatePolygonFixture(box=(40, 0.5, (15, -0.5), 0), friction=0.0, restitution=0.0)
    walls.CreatePolygonFixture(box=(40, 0.5, (15, W_ARENA + 0.5), 0), friction=0.0, restitution=0.0)
    walls.CreatePolygonFixture(box=(0.5, W_ARENA/2, (-0.5, W_ARENA/2), 0), friction=0.0, restitution=0.0)
    hw_w, hw_y = WALL_THICK / 2, (W_ARENA - EXIT_SIZE) / 4
    walls.CreatePolygonFixture(box=(hw_w, hw_y, (SLIT1_X, hw_y), 0), friction=0.0, restitution=0.0)
    walls.CreatePolygonFixture(box=(hw_w, hw_y, (SLIT1_X, W_ARENA - hw_y), 0), friction=0.0, restitution=0.0)
    walls.CreatePolygonFixture(box=(hw_w, hw_y, (SLIT2_X, hw_y), 0), friction=0.0, restitution=0.0)
    walls.CreatePolygonFixture(box=(hw_w, hw_y, (SLIT2_X, W_ARENA - hw_y), 0), friction=0.0, restitution=0.0)

    load = TLoad(world)

    running, paused, step_once = True, False, False
    gillespie_time, box2d_time = 0.0, 0.0
    STEPS_PER_FRAME = 10 
    
    victory_recorded = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE: paused = not paused
                elif event.key == pygame.K_RIGHT and paused: step_once = True

        if not paused or step_once:
            step_once = False
            
            if not victory_recorded and load.body.position.x > SLIT2_X + (L_STEM / 2) + 0.5:
                victory_recorded = True
                paused = True 
                continue 

            for _ in range(STEPS_PER_FRAME):
                while box2d_time >= gillespie_time:
                    empty_sites = [s for s in load.sites if s['state'] == 'empty']
                    info_sites  = [s for s in load.sites if s['state'] == 'info']
                    pull_sites  = [s for s in load.sites if s['state'] == 'puller']
                    lift_sites  = [s for s in load.sites if s['state'] == 'lifter']
                    
                    assert len(empty_sites) + len(info_sites) + len(pull_sites) + len(lift_sites) == N_MAX

                    R_att    = K_ON     * len(empty_sites)
                    R_forget = K_FORGET * len(info_sites)
                    R_det    = K_OFF    * (len(pull_sites) + len(lift_sites))
                    R_orient = K_ORIENT * (len(pull_sites) + len(info_sites))

                    R_c = 0.0
                    rc_items = []
                    for s in pull_sites + lift_sites:
                        v_loc_raw = load.body.GetLinearVelocityFromLocalPoint(s['local_pos'])
                        if v_loc_raw.length > 0.05:
                            v_loc_raw.Normalize()
                            v_loc = b2Vec2(v_loc_raw.x * 0.05, v_loc_raw.y * 0.05)
                        else:
                            v_loc = b2Vec2(v_loc_raw.x, v_loc_raw.y)
                        
                        f_loc = b2Vec2(v_loc.x * GAMMA_LIN, v_loc.y * GAMMA_LIN)
                        wd    = load.body.GetWorldVector(s['pull_dir'])
                        dot   = wd.x * f_loc.x + wd.y * f_loc.y
                        
                        exponent = max(-30.0, min(30.0, (dot / F_IND) * (1 if s['state'] == 'lifter' else -1)))
                        rate  = K_C * math.exp(exponent)
                        rc_items.append((s, rate))
                        R_c += rate

                    R_tot = R_att + R_forget + R_c + R_det + R_orient

                    if R_tot < 1e-12:
                        gillespie_time = box2d_time + DT
                        break

                    delta_t = math.log(1.0 / random.random()) / R_tot
                    gillespie_time += delta_t

                    r2 = random.random() * R_tot
                    if r2 < R_att:
                        s = random.choice(empty_sites)
                        if random.random() < P_INFORMED_TEST:
                            s['state'] = 'info'
                            s['pull_dir'] = b2Vec2(s['normal'].x, s['normal'].y)
                        else:
                            s['state'] = 'puller' if random.random() < 0.5 else 'lifter'
                            s['pull_dir'] = b2Vec2(s['normal'].x, s['normal'].y)

                    elif r2 < R_att + R_forget:
                        s = random.choice(info_sites)
                        s['state'] = 'puller' if random.random() < 0.5 else 'lifter'
                    elif r2 < R_att + R_forget + R_c:
                        r_sel, acum = random.random() * R_c, 0.0
                        for s, rate in rc_items:
                            acum += rate
                            if acum >= r_sel:
                                s['state'] = 'puller' if s['state'] == 'lifter' else 'lifter'
                                break
                    elif r2 < R_att + R_forget + R_c + R_det:
                        random.choice(pull_sites + lift_sites)['state'] = 'empty'
                    else:
                        s = random.choice(pull_sites + info_sites)
                        wp = load.body.GetWorldPoint(s['local_pos'])
                        if s['state'] == 'info':
                            d_world = target_for_site(wp) - wp
                        else:
                            v_loc_raw = load.body.GetLinearVelocityFromLocalPoint(s['local_pos'])
                            d_world = b2Vec2(v_loc_raw.x * GAMMA_LIN, v_loc_raw.y * GAMMA_LIN)
                            
                        if d_world.length > 0.01:
                            d_world.Normalize()
                            d_local = load.body.GetLocalVector(d_world)
                            s['pull_dir'] = clamp_to_phi_max(d_local, s['normal'])

                N_att = len([s for s in load.sites if s['state'] != 'empty'])
                N_eff = max(N_att, N0)
                
                v = load.body.linearVelocity
                w = load.body.angularVelocity
                f_drag_x = max(-abs(load.body.mass * v.x / DT), min(abs(load.body.mass * v.x / DT), -GAMMA_LIN * N_eff * v.x))
                f_drag_y = max(-abs(load.body.mass * v.y / DT), min(abs(load.body.mass * v.y / DT), -GAMMA_LIN * N_eff * v.y))
                t_drag   = max(-abs(load.body.inertia * w / DT), min(abs(load.body.inertia * w / DT), -GAMMA_ROT * N_eff * w))
                
                load.body.ApplyForceToCenter(b2Vec2(f_drag_x, f_drag_y), wake=True)
                load.body.ApplyTorque(t_drag, wake=True)

                for s in [s for s in load.sites if s['state'] in ('info', 'puller')]:
                    wp = load.body.GetWorldPoint(s['local_pos'])
                    wd = load.body.GetWorldVector(s['pull_dir'])
                    load.body.ApplyForce(force=b2Vec2(wd.x * F0, wd.y * F0), point=wp, wake=True)

                world.Step(DT, 10, 10)
                box2d_time += DT

        screen.fill((240, 240, 240))
        for fix in walls.fixtures:
            verts = [(walls.transform * v) * PPM for v in fix.shape.vertices]
            verts = [(int(v[0]), int(SCREEN_H - v[1])) for v in verts]
            pygame.draw.polygon(screen, (100, 100, 100), verts)

        for fix in load.body.fixtures:
            verts = [(load.body.transform * v) * PPM for v in fix.shape.vertices]
            verts = [(int(v[0]), int(SCREEN_H - v[1])) for v in verts]
            pygame.draw.polygon(screen, (200, 50, 50), verts)

        col = {'info': (0,0,255), 'puller': (0,200,0), 'lifter': (20,20,20), 'empty': (190,190,190)}
        for s in load.sites:
            wp  = load.body.GetWorldPoint(s['local_pos'])
            px, py  = int(wp.x * PPM), int((W_ARENA - wp.y) * PPM)
            pygame.draw.circle(screen, col[s['state']], (px, py), 3)
            
            if s['state'] in ('info', 'puller'):
                wd = load.body.GetWorldVector(s['pull_dir'])
                pygame.draw.line(screen, (255,140,0), (px,py), (int(px + wd.x*10), int(py - wd.y*10)), 1)

        if victory_recorded:
            hud = [
                f"¡VICTORIA! T entera ha cruzado. Pausado.",
                f"TIEMPO EXACTO: {box2d_time:.1f} s",
                f"Sincronización total con el CSV asegurada."
            ]
            color_text = (0, 150, 0)
        else:
            n_i = len([s for s in load.sites if s['state'] == 'info'])
            n_p = len([s for s in load.sites if s['state'] == 'puller'])
            n_l = len([s for s in load.sites if s['state'] == 'lifter'])
            hud = [
                f"TIEMPO DE LAS HORMIGAS: {box2d_time:.1f} s",
                f"N_att={n_i + n_p + n_l}/{N_MAX} | Info={n_i} | Pull={n_p} | Lift={n_l}"
            ]
            color_text = (0, 0, 0)
            
        for i, txt in enumerate(hud): 
            screen.blit(font.render(txt, True, color_text), (8, 8 + i*22))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    run_simulation()