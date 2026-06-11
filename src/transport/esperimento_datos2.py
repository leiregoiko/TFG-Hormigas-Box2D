import os
import csv
import Box2D
from Box2D import b2World, b2Vec2
import random
import math
import time

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

DT       = 1.0 / 60.0

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
    
    # 1. Identificar segmentos exteriores válidos
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

    # 2. Repartir EXACTAMENTE N_MAX (120) puntos proporcionalmente
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
        
    assert len(sites) == N_MAX, "Error crítico: No se han generado exactamente N_MAX sitios."
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

def run_trial(p_informed, seed, max_time=3000.0):
    random.seed(seed)
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

    load_body = world.CreateDynamicBody(position=(4.0, W_ARENA / 2), angle=0.0, linearDamping=0.0, angularDamping=0.0)
    load_body.bullet = True 
    hw, hs, ll, ls = L_WIDTH / 2, L_STEM / 2, L_LONG / 2, L_SHORT / 2
    load_body.CreatePolygonFixture(box=(hs, hw, (0, 0), 0), density=1.0, friction=0.0, restitution=0.0)
    load_body.CreatePolygonFixture(box=(hw, ll, (-hs, 0), 0), density=1.0, friction=0.0, restitution=0.0)
    load_body.CreatePolygonFixture(box=(hw, ls, ( hs, 0), 0), density=1.0, friction=0.0, restitution=0.0)
    sites = generate_attachment_sites()

    gillespie_time = 0.0
    box2d_time = 0.0
    
    sum_n_att = 0
    sum_vx = 0.0
    steps = 0
    success = False

    while box2d_time < max_time:
        # ARREGLO META: La T entera debe pasar la rendija
        if load_body.position.x > SLIT2_X + (L_STEM / 2) + 0.5:
            success = True
            break

        while box2d_time >= gillespie_time:
            empty_sites = [s for s in sites if s['state'] == 'empty']
            info_sites  = [s for s in sites if s['state'] == 'info']
            pull_sites  = [s for s in sites if s['state'] == 'puller']
            lift_sites  = [s for s in sites if s['state'] == 'lifter']
            
            # --- ASSERT DE SEGURIDAD FÍSICA ---
            assert len(empty_sites) + len(info_sites) + len(pull_sites) + len(lift_sites) == N_MAX
            assert len(info_sites) >= 0 and len(pull_sites) >= 0 and len(lift_sites) >= 0

            R_att    = K_ON     * len(empty_sites)
            R_forget = K_FORGET * len(info_sites)
            R_det    = K_OFF    * (len(pull_sites) + len(lift_sites))
            R_orient = K_ORIENT * (len(pull_sites) + len(info_sites))

            R_c = 0.0
            rc_items = []
            for s in pull_sites + lift_sites:
                v_loc_raw = load_body.GetLinearVelocityFromLocalPoint(s['local_pos'])
                if v_loc_raw.length > 0.05:
                    v_loc_raw.Normalize()
                    v_loc = b2Vec2(v_loc_raw.x * 0.05, v_loc_raw.y * 0.05)
                else:
                    v_loc = b2Vec2(v_loc_raw.x, v_loc_raw.y)
                
                f_loc = b2Vec2(v_loc.x * GAMMA_LIN, v_loc.y * GAMMA_LIN)
                wd    = load_body.GetWorldVector(s['pull_dir'])
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
                if random.random() < p_informed:
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
                wp = load_body.GetWorldPoint(s['local_pos'])
                if s['state'] == 'info':
                    d_world = target_for_site(wp) - wp
                else:
                    v_loc_raw = load_body.GetLinearVelocityFromLocalPoint(s['local_pos'])
                    d_world = b2Vec2(v_loc_raw.x * GAMMA_LIN, v_loc_raw.y * GAMMA_LIN)
                    
                if d_world.length > 0.01:
                    d_world.Normalize()
                    d_local = load_body.GetLocalVector(d_world)
                    s['pull_dir'] = clamp_to_phi_max(d_local, s['normal'])

        N_att = len([s for s in sites if s['state'] != 'empty'])
        
        # --- ARREGLO FÍSICO DE AUDITORÍA: El paper pide max(N_att, N0) ---
        N_eff = max(N_att, N0)
        
        v = load_body.linearVelocity
        w = load_body.angularVelocity
        f_drag_x = max(-abs(load_body.mass * v.x / DT), min(abs(load_body.mass * v.x / DT), -GAMMA_LIN * N_eff * v.x))
        f_drag_y = max(-abs(load_body.mass * v.y / DT), min(abs(load_body.mass * v.y / DT), -GAMMA_LIN * N_eff * v.y))
        t_drag   = max(-abs(load_body.inertia * w / DT), min(abs(load_body.inertia * w / DT), -GAMMA_ROT * N_eff * w))
        
        load_body.ApplyForceToCenter(b2Vec2(f_drag_x, f_drag_y), wake=True)
        load_body.ApplyTorque(t_drag, wake=True)

        for s in [s for s in sites if s['state'] in ('info', 'puller')]:
            wp = load_body.GetWorldPoint(s['local_pos'])
            wd = load_body.GetWorldVector(s['pull_dir'])
            load_body.ApplyForce(force=b2Vec2(wd.x * F0, wd.y * F0), point=wp, wake=True)

        world.Step(DT, 10, 10)
        box2d_time += DT

        sum_n_att += N_att
        sum_vx += load_body.linearVelocity.x
        steps += 1

    return {
        'Seed': seed,
        'P_Informed': str(round(p_informed, 2)).replace('.', ','), 
        'Exito': 1 if success else 0,
        'Tiempo_Segundos': str(round(box2d_time, 2)).replace('.', ','),
        'N_att_Medio': str(round(sum_n_att / steps, 2)).replace('.', ',') if steps > 0 else "0",
        'V_x_Media_cm_s': str(round((sum_vx / steps) * 100, 3)).replace('.', ',') if steps > 0 else "0"
    }

if __name__ == "__main__":
    print("--- INICIANDO BATERÍA DE SIMULACIONES CIEGAS ---")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    
    csv_file = os.path.join(data_dir, "resultados_fase.csv")
    p_values = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    trials_per_p = 10  # AHORA JUEGA 10 VECES POR PROBABILIDAD (PARA MEJORES MEDIAS)
    base_seed = 42

    resultados = []
    start_time = time.time()

    for p in p_values:
        print(f"\nTesteando P_Informed = {round(p*100)}% ...")
        for trial in range(trials_per_p):
            seed = base_seed + int(p*100) + trial
            print(f"  -> Trial {trial+1}/{trials_per_p} (Seed: {seed})... ", end="", flush=True)
            res = run_trial(p_informed=p, seed=seed, max_time=3000.0)
            resultados.append(res)
            estado = "ÉXITO" if res['Exito'] == 1 else "FRACASO"
            print(f"Resultado: {estado} en {res['Tiempo_Segundos']} s | V_x={res['V_x_Media_cm_s']} cm/s")

    with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=resultados[0].keys(), delimiter=';')
        writer.writeheader()
        for r in resultados:
            writer.writerow(r)

    print(f"\n--- EXPERIMENTO COMPLETADO EN {round(time.time() - start_time, 1)} SEGUNDOS ---")