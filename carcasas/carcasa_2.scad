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
pant_h        = 75;   // alto de la placa/módulo completo (medido: 7.5 cm)
pant_d        = 12;   // profundidad (placa + conector + relieve trasero) -- sin medir, valor típico
pant_activo_w = 112;  // ancho del área visible (mismo margen de 8mm que antes)
pant_activo_h = 67;   // alto del área visible (mismo margen de 8mm que antes)
pant_hueco_dx = 104;  // separación de huecos de montaje en X (si tu placa
pant_hueco_dy = 60;   //   los trae; si no, se puede fijar solo con el marco)

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
lector_d        = 80;  // profundidad del cuerpo del lector (hacia adentro) -- SIN MEDIR, valor típico anterior
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
pared      = 3.0;   // grosor de pared (bueno para FDM, 0.4mm boquilla)
margen     = 12;    // margen interno alrededor de cada componente
divisor_h  = 8;      // grosor del estante divisor pantalla/lector

caja_w = max(pant_w, lector_w) + 2 * margen;                  // ancho externo
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


// ============================================================================
// TAPA TRASERA
// ============================================================================
module tapa_trasera() {
    espesor = pared;
    difference() {
        union() {
            caja_redondeada(caja_w, caja_h, espesor, 6);

            // Reborde que encaja dentro de la carcasa frontal (queda a
            // presión / guía para los tornillos)
            translate([pared + 1, pared + 1, espesor])
                difference() {
                    caja_redondeada(caja_w - 2 * pared - 2, caja_h - 2 * pared - 2, 4, 3);
                    translate([pared, pared, -1])
                        caja_redondeada(caja_w - 4 * pared - 2, caja_h - 4 * pared - 2, 6, 2);
                }
        }

        // Agujeros para los tornillos que sujetan la tapa a los bosses
        // de la carcasa frontal (mismo patrón que los postes traseros)
        for (pos = [
            [pared + 6, pared + 6],
            [caja_w - pared - 6, pared + 6],
            [pared + 6, caja_h - pared - 6],
            [caja_w - pared - 6, caja_h - pared - 6],
            [caja_w / 2, pared + 6],
            [caja_w / 2, caja_h - pared - 6],
        ])
            translate([pos[0], pos[1], -1])
                cylinder(d = tornillo_d, h = espesor + 2);

        // Ranuras "ojo de cerradura" para colgar en la pared (2, cerca
        // de la parte superior)
        translate([caja_w * 0.3, caja_h - 22, -1])
            linear_extrude(espesor + 2) keyhole();
        translate([caja_w * 0.7, caja_h - 22, -1])
            linear_extrude(espesor + 2) keyhole();

        // Huecos de tornillo simples cerca de la parte inferior (además
        // de los "ojo de cerradura" de arriba, para fijar bien la parte
        // baja de la caja a la pared)
        translate([caja_w * 0.3, 18, -1]) cylinder(d = 4.5, h = espesor + 2);
        translate([caja_w * 0.7, 18, -1]) cylinder(d = 4.5, h = espesor + 2);

        // Entrada de cable de alimentación (con pasacable/prensaestopa)
        translate([caja_w / 2, 14, -1]) cylinder(d = 9, h = espesor + 2);
    }
}

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
