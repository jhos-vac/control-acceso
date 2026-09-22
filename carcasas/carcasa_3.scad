// ============================================================================
// Carcasa - Terminal de Control de Acceso
// ============================================================================
// Caja de pared/escritorio para: Raspberry Pi 4, pantalla táctil HDMI 5"
// 800x480, y lector de código QR 2D omnidireccional "de Mesa" (WD-1012).
// Diseñada para impresión 3D FDM (ver notas de impresión al final).
//
// IMPORTANTE - ANTES DE IMPRIMIR:
// El ancho/alto de la pantalla y el ancho/alto/diámetro de ventana del
// lector ya están actualizados con medidas reales dadas por el usuario.
// Todavía quedan dos valores en valor típico/placeholder (revisar antes
// de imprimir): pant_d y lector_d (cuánto sobresale cada componente
// hacia adentro de la carcasa) y pant_hueco_dx/dy (huecos de montaje de
// la pantalla, si tu placa los trae). El resto del archivo se recalcula
// solo a partir de esos parámetros.
//
// Cómo usar este archivo:
//   1. Instala OpenSCAD (gratis): https://openscad.org/downloads.html
//   2. Abre este archivo. F5 = vista previa rápida, F6 = render final.
//   3. Cambia la variable `pieza` (abajo) para exportar cada parte por
//      separado a STL: File > Export > Export as STL
//   4. Imprime "frontal" con la cara frontal contra la cama (boca abajo)
//      para que el corte de pantalla y del lector queden limpios.
// ============================================================================

// ---- Qué renderizar --------------------------------------------------
// "ensamble"   -> las dos piezas juntas, como quedaría armado
// "explosion"  -> las dos piezas separadas, para entender el armado
// "frontal"    -> solo la carcasa frontal (para exportar a STL)
// "trasera"    -> solo la tapa trasera (para exportar a STL)
pieza = "ensamble";

$fn = 48; // suavidad de curvas/cilindros

// ============================================================================
// PARÁMETROS - Raspberry Pi 4 Model B (medidas oficiales, no requieren ajuste)
// ============================================================================
pi_w        = 85;   // ancho de la placa
pi_d        = 56;   // profundidad de la placa
pi_h        = 22;   // alto libre necesario (placa + conectores + disipador)
pi_hueco_dx = 58;   // separación de huecos de montaje en X (spec oficial)
pi_hueco_dy = 49;   // separación de huecos de montaje en Y (spec oficial)
pi_hueco_d  = 2.8;  // diámetro de hueco para tornillo autorroscante M2.5

// ============================================================================
// PARÁMETROS - Pantalla táctil HDMI 5" 800x480 -- MEDIDA (ancho/alto)
// ============================================================================
// ancho ("largo", 12 cm) y alto ("ancho", 7.5 cm) medidos por el usuario.
// pant_d (profundidad) y los huecos de montaje siguen sin medir, se
// dejan en su valor típico anterior.
pant_w        = 120;  // ancho de la placa/módulo completo (medido: 12 cm)
pant_h        = 95;   // alto de la placa/módulo completo (medido: 7.5 cm)
pant_d        = 6;   // profundidad (placa + conector + relieve trasero) -- sin medir, valor típico
pant_activo_w = 120;  // ancho del área visible (mismo margen de 8mm que antes)
pant_activo_h = 75;   // alto del área visible (mismo margen de 8mm que antes)
pant_hueco_dy = 85;  // separación de huecos de montaje en X (si tu placa
pant_hueco_dx = 60;   //   los trae; si no, se puede fijar solo con el marco)

// ============================================================================
// PARÁMETROS - Lector QR 2D Omnidireccional "de Mesa" (WD-1012) -- MEDIDA
// ============================================================================
// alto (15.5 cm), ancho (10 cm) y diámetro de la ventana/lente de
// lectura (8 cm) medidos por el usuario. lector_d (cuánto sobresale el
// cuerpo hacia adentro de la carcasa) sigue sin medir -- coincide en
// número con el diámetro de la ventana pero es un dato distinto, no
// los confundas si vuelves a ajustar esto.
lector_w        = 100; // ancho del cuerpo del lector (medido: 10 cm)
lector_h        = 155; // alto del cuerpo del lector (medido: 15.5 cm)
lector_d        = 100;  // profundidad del cuerpo del lector (hacia adentro) -- SIN MEDIR, valor típico anterior
lector_vent_d   = 80;  // diámetro de la ventana/lente de lectura (medido: 8 cm)

// La ventana NO está centrada en el cuerpo del lector: según la foto
// de la plantilla/footprint que mandaste, la parte de arriba del
// cuerpo es donde van los tornillos de montaje y el conector/cable, y
// la lente queda más abajo, hacia el tercio inferior. offset_y
// desplaza el centro de la ventana hacia ABAJO (valor positivo) desde
// el centro geométrico del cuerpo del lector; offset_x la desplaza
// hacia la derecha (positivo) u izquierda (negativo).
// *** ESTO ES UNA ESTIMACIÓN visual a partir de tu foto, no una
// medida exacta -- confirmá/corregí con el lector en mano (medí desde
// el borde inferior del cuerpo hasta el centro de la lente). ***
lector_vent_offset_x = 0;    // mm, + = hacia la derecha (a ojo, se ve centrada en X)
lector_vent_offset_y = 20;   // mm, + = hacia abajo (estimado de la foto, AJUSTAR)

// ============================================================================
// PARÁMETROS - Carcasa general
// ============================================================================
pared      = 5.0;   // grosor de pared (bueno para FDM, 0.4mm boquilla)
margen     = 12;    // margen interno alrededor de cada componente
divisor_h  = 8;      // grosor del estante divisor pantalla/lector

caja_w = max(pant_w, lector_w) + 3 * margen;                  // ancho externo
caja_h_pantalla = pant_h + 2 * margen;                        // sección pantalla
caja_h_lector   = lector_h + 2 * margen;                      // sección lector
caja_h = caja_h_pantalla + divisor_h + caja_h_lector;         // alto externo
caja_d = lector_d + pared + 8;                                // profundidad externa

tornillo_d = 3.2; // hueco piloto para tornillo M3 (unión frontal/trasera)

echo(str("Medidas externas de la carcasa: ", caja_w, " x ", caja_h, " x ", caja_d, " mm"));

// ============================================================================
// MÓDULOS AUXILIARES
// ============================================================================

module caja_redondeada(w, h, d, r) {
    // Prisma con esquinas verticales redondeadas, centrado en X/Y, apoyado en Z=0
    hull() {
        for (x = [r, w - r], y = [r, h - r]) {
            translate([x, y, 0])
                cylinder(r = r, h = d);
        }
    }
}

module poste(alto, d_ext = 6, d_hueco = pi_hueco_d) {
    difference() {
        cylinder(d = d_ext, h = alto);
        translate([0, 0, alto - 6])
            cylinder(d = d_hueco, h = 6.1);
    }
}

module keyhole(d_grande = 9, d_chico = 4.5, largo = 12) {
    // Ranura tipo "ojo de cerradura" para colgar de un tornillo en la pared
    union() {
        translate([0, largo, 0]) circle(d = d_grande);
        translate([-d_chico / 2, 0, 0]) square([d_chico, largo]);
        circle(d = d_chico);
    }
}

// ============================================================================
// CARCASA FRONTAL
// ============================================================================
module carcasa_frontal() {
    centro_x = caja_w / 2;
    // Y=0 es la parte inferior de la caja (donde va el lector)
    y_lector_centro   = caja_h_lector / 2;
    y_divisor_centro  = caja_h_lector + divisor_h / 2;
    y_pantalla_centro = caja_h_lector + divisor_h + caja_h_pantalla / 2;

    difference() {
        union() {
            // Cascarón exterior (abierto atrás)
            difference() {
                caja_redondeada(caja_w, caja_h, caja_d, 6);
                translate([pared, pared, pared])
                    caja_redondeada(caja_w - 2 * pared, caja_h - 2 * pared, caja_d, 4);
            }

            // Estante divisor entre sección pantalla y sección lector,
            // con una abertura central para pasar cables entre ambas.
            translate([pared, y_divisor_centro - divisor_h / 2, 0])
                difference() {
                    cube([caja_w - 2 * pared, divisor_h, caja_d - pared]);
                    translate([caja_w / 2 - pared, -1, pared])
                        cube([2 * pared, divisor_h + 2, caja_d - 3 * pared]);
                }

            // Postes de montaje para la Raspberry Pi 4, sobre el estante
            // divisor (la Pi queda "de pie" apoyada sobre el divisor,
            // puertos hacia la sección del lector para fácil acceso de cables)
      
            // Postes de montaje para la pantalla, pegados a la cara frontal
         
            // Repisa + guías para el lector (bahía abierta por detrás para
            // insertarlo y cablearlo; se asegura con una brida/zip-tie
            // pasando por las ranuras, ya que sus medidas reales pueden
            // variar del placeholder usado aquí)
                translate([centro_x - lector_w / 2 - 2, y_lector_centro - lector_h / 2 - 2, pared])
                difference() {
                    cube([lector_w + 4, lector_h + 4, 2]);
            
                    // ranuras para brida (zip-tie), una cerca del frente y
                    // otra cerca del fondo de la bahía
                    translate([lector_w / 2 + 4 - 3, 4, -1]) cube([6, 3, 4]);
                    translate([lector_w / 2 + 4 - 3, lector_h + 4 - 7, -1]) cube([6, 3, 4]);
                }
            translate([centro_x - lector_w / 2 - 2, y_lector_centro - lector_h / 2 - 2, pared])
                cube([4, lector_h + 4, lector_d * 0.6]); // riel guía izquierdo
            translate([centro_x + lector_w / 2 - 2, y_lector_centro - lector_h / 2 - 2, pared])
                cube([4, lector_h + 4, lector_d * 0.6]); // riel guía derecho

            // Bosses para atornillar la tapa trasera (perímetro interior)
            for (pos = [
                [pared + 6, pared + 6],
                [caja_w - pared - 6, pared + 6],
                [pared + 6, caja_h - pared - 6],
                [caja_w - pared - 6, caja_h - pared - 6],
                [caja_w / 2, pared + 6],
                [caja_w / 2, caja_h - pared - 6],
            ])
                translate([pos[0], pos[1], 0])
                    poste(caja_d - pared - 2, d_ext = 8, d_hueco = tornillo_d);
        }

        // Ventana de visualización de la pantalla (recorte frontal)
        translate([centro_x - pant_activo_w / 2, y_pantalla_centro - pant_activo_h / 2, -1])
            cube([pant_activo_w, pant_activo_h, pared + 2]);

        // Ventana de lectura del lector QR (recorte frontal, circular:
        // el dato que diste fue un diámetro, antes era un recorte
        // cuadrado de 55x55 porque no se conocía la forma real).
        // No está centrada en el cuerpo del lector -- ver
        // lector_vent_offset_x/y arriba (estimado de tu foto, revisar).
        translate([centro_x + lector_vent_offset_x, y_lector_centro - lector_vent_offset_y, -1])
            cylinder(d = lector_vent_d, h = pared + 2);

        // Rejilla de ventilación (pared lateral derecha, a la altura de la Pi)
        for (i = [0:8])
            translate([caja_w - pared - 1, y_divisor_centro + 8 + i * 4, caja_d - 25])
                cube([pared + 2, 2, 20]);

        // Paso de cables (alimentación / red) por la pared inferior,
        // alineado con el lado de puertos de la Pi
        translate([centro_x -20, -1, caja_d - 25])
            cube([40, pared + 2, 15]);
    }
}

// ============================================================================
// TAPA TRASERA
// ============================================================================

// ENSAMBLE / EXPORTACIÓN
// ============================================================================
if (pieza == "frontal") {
    carcasa_frontal();
} else if (pieza == "trasera") {
    tapa_trasera();
} else if (pieza == "explosion") {
    carcasa_frontal();
    translate([0, 0, -caja_d - 40])
        tapa_trasera();
} else {
    // "ensamble": tapa trasera en su lugar real, pegada a la parte
    // de atrás de la carcasa frontal
    carcasa_frontal();
    translate([0, 0, -pared])
        tapa_trasera();
}
