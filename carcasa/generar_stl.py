"""
Genera los archivos STL de la carcasa (lista para imprimir) directamente
en Python, sin depender de OpenSCAD (que no se pudo instalar en este
entorno por falta de acceso a internet para paquetes).

El diseño "fuente de verdad" sigue siendo `carcasa.scad` (más preciso y
editable, con esquinas redondeadas, postes cilíndricos, etc.). Este
script genera una versión geométricamente equivalente pero construida
con formas simples (cajas rectangulares) para poder generar la malla a
mano con numpy, sin librerías de CAD:

  - Esquinas cuadradas en vez de redondeadas.
  - Postes de montaje cuadrados en vez de cilíndricos, SIN el hueco
    piloto del tornillo modelado (hay que taladrar el piloto a mano:
    ~2.5mm para los postes de la Pi/pantalla, ~3mm para unir las dos
    piezas). Esto es una práctica común y confiable para piezas
    impresas en 3D con huecos pequeños.
  - Ranuras "ojo de cerradura" simplificadas a ranuras rectangulares
    (funcionan igual para colgar de un tornillo).

Genera dos archivos STL binarios, cada uno ya orientado y apoyado sobre
el plano Z=0 en la posición recomendada para imprimir:

  - carcasa_frontal.stl  (imprimir con la cara frontal contra la cama)
  - tapa_trasera.stl     (imprimir plana, tal cual)

Requiere: numpy (ya instalado en este entorno). No requiere OpenSCAD,
trimesh, ni ninguna librería de CAD.
"""
import struct
import numpy as np

# ---------------------------------------------------------------------------
# Mismos parámetros que carcasa.scad / generar_vistas.py
# ---------------------------------------------------------------------------
pi_w, pi_d, pi_h = 85, 56, 22
pi_hueco_dx, pi_hueco_dy = 58, 49

pant_w, pant_h, pant_d = 120, 76, 12
pant_activo_w, pant_activo_h = 112, 68
pant_hueco_dx, pant_hueco_dy = 104, 60

lector_w, lector_h, lector_d = 100, 100, 80
lector_vent_w, lector_vent_h = 55, 55

pared = 3.0
margen = 12
divisor_h = 8

caja_w = max(pant_w, lector_w) + 2 * margen
caja_h_lector = lector_h + 2 * margen
caja_h_pantalla = pant_h + 2 * margen
caja_h = caja_h_lector + divisor_h + caja_h_pantalla
caja_d = lector_d + pared + 8

# Convención de coordenadas de este script (propia, para generar la malla):
#   X = ancho     (0..caja_w)
#   Y = profundidad, Y=0 es la CARA FRONTAL (0..caja_d)
#   Z = altura, Z=0 es la parte de ABAJO -- sección del lector (0..caja_h)

EPS = 0.03  # pequeño solape entre cajas vecinas, evita micro-huecos al cortar

triangulos_frontal = []
triangulos_trasera = []


# ---------------------------------------------------------------------------
# Utilidades de malla
# ---------------------------------------------------------------------------
def _cara(v0, v1, v2, v3, normal_esperada):
    """Devuelve 2 triángulos para un cuadrilátero, verificando que el
    orden quede con la normal apuntando hacia normal_esperada (si no,
    invierte el orden)."""
    p0, p1, p2 = np.array(v0), np.array(v1), np.array(v2)
    n = np.cross(p1 - p0, p2 - p0)
    if np.dot(n, normal_esperada) < 0:
        v0, v1, v2, v3 = v3, v2, v1, v0
    return [(v0, v1, v2), (v0, v2, v3)]


def box_triangles(lo, hi):
    """12 triángulos de una caja alineada a los ejes, normales hacia
    afuera garantizadas por construcción (se verifican, no se asumen)."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    v000, v100 = (x0, y0, z0), (x1, y0, z0)
    v110, v010 = (x1, y1, z0), (x0, y1, z0)
    v001, v101 = (x0, y0, z1), (x1, y0, z1)
    v111, v011 = (x1, y1, z1), (x0, y1, z1)

    tris = []
    tris += _cara(v000, v010, v110, v100, (0, 0, -1))   # abajo
    tris += _cara(v001, v101, v111, v011, (0, 0, 1))    # arriba
    tris += _cara(v000, v100, v101, v001, (0, -1, 0))   # frente (Y bajo)
    tris += _cara(v010, v011, v111, v110, (0, 1, 0))    # atrás (Y alto)
    tris += _cara(v000, v001, v011, v010, (-1, 0, 0))   # izquierda
    tris += _cara(v100, v110, v111, v101, (1, 0, 0))    # derecha
    return tris


def _grid_menos_huecos(u0, u1, v0, v1, huecos):
    """Rectángulo [u0,u1]x[v0,v1] menos una lista de rectángulos-hueco
    (cada uno (hu0,hu1,hv0,hv1)); devuelve una lista de rectángulos
    sólidos que rellenan lo que queda, fusionando celdas vecinas en la
    misma fila para no generar de más."""
    xs = sorted({u0, u1, *[c for h in huecos for c in (h[0], h[1])]})
    xs = [x for x in xs if u0 - 1e-9 <= x <= u1 + 1e-9]
    ys = sorted({v0, v1, *[c for h in huecos for c in (h[2], h[3])]})
    ys = [y for y in ys if v0 - 1e-9 <= y <= v1 + 1e-9]

    celdas = []  # (x0,x1,y0,y1)
    for j in range(len(ys) - 1):
        cy0, cy1 = ys[j], ys[j + 1]
        if cy1 - cy0 < 1e-6:
            continue
        fila = []
        for i in range(len(xs) - 1):
            cx0, cx1 = xs[i], xs[i + 1]
            if cx1 - cx0 < 1e-6:
                continue
            cxm, cym = (cx0 + cx1) / 2, (cy0 + cy1) / 2
            dentro_hueco = any(h[0] <= cxm <= h[1] and h[2] <= cym <= h[3] for h in huecos)
            if not dentro_hueco:
                fila.append([cx0, cx1])
        # fusiona celdas contiguas de la misma fila
        fila_fusionada = []
        for c in fila:
            if fila_fusionada and abs(fila_fusionada[-1][1] - c[0]) < 1e-6:
                fila_fusionada[-1][1] = c[1]
            else:
                fila_fusionada.append(c)
        for c in fila_fusionada:
            celdas.append((c[0], c[1], cy0, cy1))
    return celdas


def panel_con_huecos(lo, hi, huecos_uv):
    """Genera las cajas sólidas de un panel delgado (detecta solo el eje
    fino automáticamente) al que se le restan huecos rectangulares
    (huecos_uv en las 2 dimensiones anchas del panel)."""
    lo, hi = np.array(lo, dtype=float), np.array(hi, dtype=float)
    tam = hi - lo
    eje_fino = int(np.argmin(tam))
    ejes_anchos = [a for a in range(3) if a != eje_fino]
    ua, va = ejes_anchos
    u0, u1 = lo[ua], hi[ua]
    v0, v1 = lo[va], hi[va]
    celdas = _grid_menos_huecos(u0, u1, v0, v1, huecos_uv)

    tris = []
    for cu0, cu1, cv0, cv1 in celdas:
        clo, chi = lo.copy(), hi.copy()
        clo[ua], chi[ua] = cu0, cu1
        clo[va], chi[va] = cv0, cv1
        tris += box_triangles(tuple(clo), tuple(chi))
    return tris


def volumen(tris):
    """Suma de volumen con signo (chequeo rápido de sanidad de la malla)."""
    v = 0.0
    for a, b, c in tris:
        a, b, c = np.array(a), np.array(b), np.array(c)
        v += np.dot(a, np.cross(b, c)) / 6.0
    return v


def escribir_stl_binario(tris, ruta, permutar=None, trasladar=(0, 0, 0)):
    """Exporta a STL binario. `permutar` reordena los ejes (p.ej. (0,2,1)
    para intercambiar Y/Z al reorientar la pieza para impresión); si la
    permutación invierte el sentido (determinante -1), se corrige el
    orden de los vértices para no dejar la pieza "al revés"."""
    if permutar is None:
        permutar = (0, 1, 2)
    signo = np.linalg.det(np.eye(3)[list(permutar)])
    tx, ty, tz = trasladar

    with open(ruta, "wb") as f:
        f.write(b"Carcasa control de acceso - generado con Python\0".ljust(80, b"\0"))
        f.write(struct.pack("<I", len(tris)))
        for tri in tris:
            pts = []
            for v in tri:
                vp = [v[permutar[0]], v[permutar[1]], v[permutar[2]]]
                pts.append((vp[0] + tx, vp[1] + ty, vp[2] + tz))
            if signo < 0:
                pts = [pts[0], pts[2], pts[1]]  # corrige el sentido (espejo)
            p0, p1, p2 = (np.array(p) for p in pts)
            n = np.cross(p1 - p0, p2 - p0)
            norma = np.linalg.norm(n)
            n = n / norma if norma > 1e-9 else np.array([0.0, 0.0, 0.0])
            f.write(struct.pack("<3f", *n))
            for p in pts:
                f.write(struct.pack("<3f", *p))
            f.write(struct.pack("<H", 0))


# ============================================================================
# CARCASA FRONTAL
# ============================================================================
tf = []

# --- Cascarón: 6 paneles gruesos que se solapan en las esquinas (para
#     que no queden micro-huecos al fusionarse) -------------------------
tf += panel_con_huecos((0, 0, 0), (caja_w, pared, caja_h), [
    # ventana de la pantalla (sección superior)
    (caja_w / 2 - pant_activo_w / 2, caja_w / 2 + pant_activo_w / 2,
     caja_h - caja_h_pantalla / 2 - pant_activo_h / 2, caja_h - caja_h_pantalla / 2 + pant_activo_h / 2),
    # ventana del lector QR (sección inferior)
    (caja_w / 2 - lector_vent_w / 2, caja_w / 2 + lector_vent_w / 2,
     caja_h_lector / 2 - lector_vent_h / 2, caja_h_lector / 2 + lector_vent_h / 2),
])  # panel frontal (Y=0..pared)

tf += panel_con_huecos((0, caja_d - pared, 0), (caja_w, caja_d, caja_h), [])  # atrás (perímetro; se cierra con la tapa)
tf += panel_con_huecos((0, 0, 0), (pared, caja_d, caja_h), [])                 # pared izquierda
tf += panel_con_huecos((caja_w - pared, 0, 0), (caja_w, caja_d, caja_h), [
    # rejilla de ventilación, a la altura de la Raspberry Pi
    (caja_d * 0.15, caja_d * 0.15 + 30, caja_h_lector + divisor_h + 10 + i * 4, caja_h_lector + divisor_h + 10 + i * 4 + 2)
    for i in range(8)
])  # pared derecha (con rejilla)
tf += panel_con_huecos((0, 0, caja_h - pared), (caja_w, caja_d, caja_h), [])   # tapa superior
tf += panel_con_huecos((0, 0, 0), (caja_w, caja_d, pared), [
    # paso de cable de alimentación/red hacia la Raspberry Pi
    (caja_w / 2 - 20, caja_w / 2 + 20, caja_d - 35, caja_d - 15),
    # ranuras para brida (zip-tie) que sostiene el lector en su bahía
    (caja_w / 2 - lector_w / 2 + 8, caja_w / 2 - lector_w / 2 + 14, 8, 20),
    (caja_w / 2 + lector_w / 2 - 14, caja_w / 2 + lector_w / 2 - 8, 8, 20),
])  # piso

# --- Estante divisor entre pantalla y lector, con abertura para cables --
tf += panel_con_huecos(
    (pared, 0, caja_h_lector), (caja_w - pared, caja_d - pared, caja_h_lector + divisor_h),
    [(caja_w / 2 - pared - 2, caja_w / 2 + pared + 2, caja_d - pared - 25, caja_d)],
)

# --- Postes de montaje de la Raspberry Pi (cuadrados, sobre el divisor) -
pi_bx0 = caja_w / 2 - pi_w / 2
pi_by0 = caja_d - pared - 15 - pi_d  # Pi hacia el fondo, cerca de la abertura de cables
poste_w = 7
z0_post_pi = caja_h_lector + divisor_h - EPS
z1_post_pi = z0_post_pi + 10
for i in (0, 1):
    for j in (0, 1):
        cx = pi_bx0 + 13.5 + i * pi_hueco_dx
        cy = pi_by0 + 3.5 + j * pi_hueco_dy
        tf += box_triangles((cx - poste_w / 2, cy - poste_w / 2, z0_post_pi),
                             (cx + poste_w / 2, cy + poste_w / 2, z1_post_pi))

# --- Postes de montaje de la pantalla (pegados a la cara frontal) ------
pant_cz = caja_h - caja_h_pantalla / 2
for sx in (-1, 1):
    for sz in (-1, 1):
        cx = caja_w / 2 + sx * pant_hueco_dx / 2
        cz = pant_cz + sz * pant_hueco_dy / 2
        tf += box_triangles((cx - poste_w / 2, pared - EPS, cz - poste_w / 2),
                             (cx + poste_w / 2, pared + 8, cz + poste_w / 2))

# --- Rieles guía para el lector QR (mantienen el aparato centrado) -----
riel_w = 4
riel_largo = lector_d * 0.6
tf += box_triangles((caja_w / 2 - lector_w / 2 - riel_w, pared - EPS, pared - EPS),
                     (caja_w / 2 - lector_w / 2, pared + riel_largo, caja_h_lector - pared))
tf += box_triangles((caja_w / 2 + lector_w / 2, pared - EPS, pared - EPS),
                     (caja_w / 2 + lector_w / 2 + riel_w, pared + riel_largo, caja_h_lector - pared))

# --- Postes cuadrados para atornillar la tapa trasera -------------------
postes_xz = [
    (pared + 8, pared + 8), (caja_w - pared - 8, pared + 8),
    (pared + 8, caja_h - pared - 8), (caja_w - pared - 8, caja_h - pared - 8),
    (caja_w / 2, pared + 8), (caja_w / 2, caja_h - pared - 8),
]
for cx, cz in postes_xz:
    tf += box_triangles((cx - 4, caja_d - pared - 12, cz - 4), (cx + 4, caja_d - pared + EPS, cz + 4))

triangulos_frontal = tf

# ============================================================================
# TAPA TRASERA (panel plano, con huecos para tornillos, colgado y cable)
# ============================================================================
huecos_tapa = []
for cx, cz in postes_xz:
    huecos_tapa.append((cx - 2, cx + 2, cz - 2, cz + 2))  # paso de tornillo M3

# ranuras "ojo de cerradura" simplificadas, para colgar en la pared
for fx in (0.3, 0.7):
    cx = caja_w * fx
    huecos_tapa.append((cx - 4.5, cx + 4.5, caja_h - 30, caja_h - 12))

# huecos de tornillo simples cerca de la parte baja
for fx in (0.3, 0.7):
    cx = caja_w * fx
    huecos_tapa.append((cx - 2.25, cx + 2.25, 14, 22))

# entrada del cable de alimentación
huecos_tapa.append((caja_w / 2 - 6, caja_w / 2 + 6, 10, 22))

triangulos_trasera = panel_con_huecos((0, caja_d - pared, 0), (caja_w, caja_d, caja_h), huecos_tapa)

# ============================================================================
# Chequeos de sanidad + exportación
# ============================================================================
print(f"Medidas externas: {caja_w:.0f} x {caja_h:.0f} x {caja_d:.0f} mm (ancho x alto x profundidad)")
print(f"Carcasa frontal: {len(triangulos_frontal)} triángulos, volumen aprox. = {volumen(triangulos_frontal):.0f} mm3")
print(f"Tapa trasera:    {len(triangulos_trasera)} triángulos, volumen aprox. = {volumen(triangulos_trasera):.0f} mm3")

# Reorientar para impresión: la cara frontal (Y=0) debe quedar apoyada en
# la cama (Z=0), con la caja "creciendo" hacia arriba en profundidad.
# Permutación (X, Z_mundo, Y_mundo) -> (X_stl, Y_stl, Z_stl):
escribir_stl_binario(
    triangulos_frontal, "/home/claude/control-acceso/carcasa/carcasa_frontal.stl",
    permutar=(0, 2, 1), trasladar=(0, 0, 0),
)

# La tapa trasera ya es delgada en Y_mundo (queda cerca de Y=caja_d);
# se aplica la misma permutación y se traslada para que apoye en Z=0.
escribir_stl_binario(
    triangulos_trasera, "/home/claude/control-acceso/carcasa/tapa_trasera.stl",
    permutar=(0, 2, 1), trasladar=(0, 0, -(caja_d - pared)),
)

print("Listos: carcasa_frontal.stl y tapa_trasera.stl")
