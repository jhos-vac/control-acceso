# Carcasa del terminal — diseño 3D

Diseño paramétrico de la caja que aloja la Raspberry Pi 4, la pantalla
táctil HDMI 5" (800x480) y el lector QR 2D omnidireccional de mesa
(WD-1012), inspirado en el kiosco de referencia que compartiste.

Se definió como **caja compacta de pared/escritorio** (no como el
totem/pedestal de piso de la foto de referencia) y pensada para
**impresión 3D FDM**, según lo que confirmaste.

## Archivos

- **`carcasa_frontal.stl` y `tapa_trasera.stl`** — **listos para
  imprimir**, ya orientados apoyados en la cama de impresión tal como
  se recomienda más abajo. Ábrelos directo en tu slicer (Cura,
  PrusaSlicer, Bambu Studio, etc.) y laminá — no hace falta rotarlos.
- `carcasa.scad` — el diseño paramétrico original, en
  [OpenSCAD](https://openscad.org/downloads.html) (gratis,
  Windows/Mac/Linux). Tiene esquinas redondeadas y postes cilíndricos
  (más prolijo visualmente); úsalo si quieres editar el diseño con
  parámetros y volver a exportar el STL vos mismo.
- `generar_stl.py` — script en Python que generó los dos STL de arriba
  directamente (sin depender de OpenSCAD, que no se pudo instalar en
  este entorno de trabajo por no tener acceso a internet para
  paquetes). Construye la geometría a mano con cajas rectangulares:
  mismas medidas y huecos que `carcasa.scad`, pero con esquinas
  cuadradas y postes cuadrados en vez de redondeados/cilíndricos, y
  **sin el hueco piloto de los tornillos modelado** (ver más abajo).
  Verificado: ambas mallas cerraron sin bordes sueltos (watertight) y
  el volumen de material calculado es coherente con las medidas.
- `esquema_3d.png` / `vistas_2d_acotadas.png` — vistas rápidas para
  entender el diseño sin instalar nada. **No son un render CAD real**,
  son un esquema aproximado (cajas simples representando cada pieza).
- `generar_vistas.py` — script que genera esas dos imágenes (no hace
  falta correrlo, ya están generadas).

### `carcasa.scad` vs. los `.stl` — qué cambia

Los STL ya están listos para imprimir tal cual, pero son una versión
simplificada del diseño en `carcasa.scad` (necesario porque tuve que
generarlos a mano en Python, sin un programa de CAD disponible en este
entorno):

| | `carcasa.scad` (OpenSCAD) | `.stl` (listos para imprimir) |
|---|---|---|
| Esquinas de la caja | Redondeadas | Cuadradas |
| Postes de montaje | Cilíndricos, con hueco piloto del tornillo ya modelado | Cuadrados, **sin** hueco piloto |
| Medidas y huecos (pantalla, lector, ventilación, cables) | — | Idénticos |

Por lo del hueco piloto: en los postes de montaje (Raspberry Pi,
pantalla, y los 6 que unen las dos piezas) vas a necesitar taladrar a
mano un huequito antes de atornillar — con una broca de ~2.5mm para
los tornillos M2.5 (Pi y pantalla) y ~3mm para los M3 (unión de las
dos piezas). Es rápido y es una práctica normal para piezas impresas
en 3D con huecos chicos (suele salir más preciso que confiar en que
el agujero impreso quede con la medida exacta).

## Medidas externas resultantes

Con los parámetros actuales: **144 x 232 x 91 mm** (ancho x alto x
profundidad). La profundidad la determina casi por completo el cuerpo
del lector QR (ver más abajo).

## ⚠️ Antes de imprimir: hay que verificar medidas

No encontré una ficha técnica confiable en línea para el modelo exacto
**"WD-1012 de Mesa"**, ni para tu pantalla HDMI 5" específica (hay
varias marcas con este formato — SunFounder, Elecrow, Waveshare, genéricas
— con pequeñas diferencias de tamaño entre sí). Así que usé:

- **Pantalla**: medidas típicas de una placa de 5" HDMI 800x480 para
  Raspberry Pi (120 x 76 mm de placa, ~112 x 68 mm de área visible).
- **Lector QR**: un tamaño de referencia típico de un lector 2D "de
  presentación/mesa" compacto (100 x 100 x 80 mm), ya que no es un
  módulo embebido como el de tu foto de referencia, sino un aparato de
  escritorio con su propia carcasa.

Todos estos valores están en un solo bloque de parámetros al inicio de
`carcasa.scad`, claramente marcados `MEDIR Y AJUSTAR`. Para ajustar:

1. Mide tus dos componentes físicos con una regla o calibrador (ancho,
   alto, profundidad, y en el caso de la pantalla, si trae huecos de
   tornillo, la separación entre ellos).
2. Cambia esos números en `carcasa.scad`.
3. El resto del archivo se recalcula solo (el tamaño de la caja, la
   ventana de cada componente, los postes de montaje).

**Nota importante sobre el lector**: como es un aparato "de mesa" (no un
módulo pensado para empotrarse, a diferencia del que se ve en tu foto de
referencia), lo diseñé para que se deslice dentro de una bahía abierta
por detrás y quede sujeto con una brida plástica (zip-tie) pasando por
dos ranuras — así no depende de que las medidas queden exactas, y es
fácil de retirar si necesitas cambiarlo. Si me pasas las medidas reales
del lector (o el enlace exacto del que compraste), puedo ajustar el
diseño para que quede más ajustado y prolijo.

## Cómo se organiza el diseño

- **Sección superior**: pantalla, montada directamente a la cara
  frontal (los postes de montaje están pegados al frente, en el patrón
  de huecos que definas).
- **Estante divisor**: separa la sección de pantalla de la de lector, y
  sirve de base para montar la Raspberry Pi "acostada" encima, con los
  puertos (USB/Ethernet/alimentación) orientados hacia el corte de
  cables en la pared inferior de la caja.
- **Sección inferior**: bahía para el lector QR, con dos rieles guía y
  ranuras para brida.
- **Tapa trasera**: pieza separada que cierra la caja por detrás y se
  atornilla a 6 postes internos. Tiene dos ranuras tipo "ojo de
  cerradura" arriba (para colgar de dos tornillos en la pared) y dos
  huecos simples abajo para fijar bien la parte baja. También tiene la
  entrada para el cable de alimentación.
- **Ventilación**: rejilla lateral a la altura de la Raspberry Pi.

## Impresión

- Material: PLA o PETG (PETG si el punto de acceso recibe sol directo o
  mucho calor; para interior normal, PLA es suficiente y más fácil de
  imprimir).
- Orientación: imprime la **carcasa frontal boca abajo** (cara frontal
  contra la cama) para que los cortes de la pantalla y del lector
  queden con buen acabado y sin necesitar soportes ahí. La **tapa
  trasera** se imprime plana, tal cual.
- Altura de capa: 0.2 mm está bien. Relleno 15-20% es más que suficiente
  para una carcasa de este tipo.
- Tornillos: M2.5 para la Raspberry Pi y la pantalla (autorroscantes en
  los postes impresos), M3 para unir carcasa frontal + tapa trasera.

## Cómo imprimir (rápido)

1. Abre `carcasa_frontal.stl` y `tapa_trasera.stl` en tu slicer — ya
   vienen orientados y apoyados sobre la cama, no hace falta rotarlos
   ni moverlos, solo laminar e imprimir.
2. Configuración sugerida: PLA o PETG, capa 0.2mm, relleno 15-20%,
   soportes en general no deberían hacer falta (paredes verticales,
   voladizos moderados) — revisa la vista previa del slicer por las
   dudas, sobre todo alrededor de los rieles del lector.
3. Después de imprimir, taladra a mano los huecos piloto de los
   postes de montaje (ver tabla arriba) antes de atornillar.

## Cómo editar el diseño (opcional, con OpenSCAD)

Si más adelante quieres cambiar medidas o el estilo de la carcasa:

1. Instala [OpenSCAD](https://openscad.org/downloads.html) (gratis).
2. Abre `carcasa.scad`. Con F5 tienes una vista previa rápida; con F6,
   el render final (más lento pero más preciso).
3. Arriba del archivo hay una variable `pieza` — cámbiala a `"frontal"`
   o `"trasera"` para exportar cada parte por separado:
   `File > Export > Export as STL`.
4. Usa `pieza = "explosion";` si quieres ver las dos piezas separadas,
   para entender mejor cómo se arma.

Si prefieres seguir generando los STL con el script de Python (por
ejemplo después de ajustar las medidas del lector/pantalla), edita los
parámetros al inicio de `generar_stl.py` (son los mismos nombres que
en `carcasa.scad`) y corre `python3 generar_stl.py`.

## Siguientes pasos sugeridos

- Confirmar medidas reales de pantalla y lector (lo más importante).
- Decidir si quieres un logo/texto institucional en relieve en la cara
  frontal (fácil de agregar una vez que el resto esté validado).
- Si más adelante el sistema migra a un terminal Raspberry Pi de verdad
  (hoy corre en PC con cámara, según el estado actual del proyecto),
  esta carcasa ya está pensada para esa Raspberry Pi 4 + pantalla +
  lector — no haría falta rediseñarla desde cero.
