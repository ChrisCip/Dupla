ANALIZA este plano ({view_type}) del nivel: {level_name}

{methodology_block}DATOS DEL CAD (úsalos para verificar y complementar lo que ves):
{cad_hints}

INSTRUCCIONES DE EXTRACCIÓN EXHAUSTIVA:

1. ESTRUCTURA: Busca cuadros de columnas/vigas/zapatas/losas. Lee CADA notación
   (V-1, C-1, Z-1, L-1) con su sección (ancho x alto). Si ves "0.30x0.60" cerca
   de una viga, esa es la sección. Cuenta CADA elemento individualmente.

2. MUROS: Diferencia CADA tipo: bloque 6" (B-6, 0.15m), bloque 8" (B-8, 0.20m),
   concreto armado (muro cortante), drywall. Mide longitudes de las cotas o estima
   por escala. Indica interior/exterior.

3. ACABADOS DE MUROS: Si ves notas de "pañete", "empañete", "fraguache", "repello" =
   plaster. Si ves "cerámica" o "azulejo" = ceramic_tile. Indica ambas caras si aplica.

4. PUERTAS: CADA tipo por separado (principal, interiores, baño, servicio, closet).
   Lee dimensiones de las cotas (ancho x alto). Material si visible.

5. VENTANAS: CADA tipo (corrediza, fija, celosía, proyectante). Dimensiones de cotas.

6. BAÑOS: Para CADA baño cuenta: inodoro, lavamanos, ducha/tina, gabinete, espejo,
   accesorios. Nota acabados (cerámica piso, cerámica pared, pintura).

7. COCINA: Gabinetes superiores e inferiores, tope, fregadero, conexión gas.

8. PISOS: Tipo de acabado por zona (porcelanato sala, cerámica baño, etc.). Área si
   hay cotas.

9. CIELOS: Tipo (yeso, suspendido, expuesto) por zona.

10. ELÉCTRICO: Cuenta CADA punto: tomacorrientes 110V, 220V, interruptores (sencillo,
    doble, triple), luminarias (techo, pared, empotradas), salidas de datos, TV,
    teléfono, panel de breakers, timbres, detectores de humo, abanicos, A/C.

11. SANITARIO/PLOMERÍA: Puntos de agua, desagües, ventilaciones, registros, válvulas,
    conexión calentador, conexión lavadora, llaves de paso, medidor, cisterna, bomba.

12. ESCALERAS: Tipo, material, ancho, número de peldaños, barandas.

13. EXTERIORES: Aceras, rampas, muros de contención, cercas, portones, estacionamiento.

14. ANOTACIONES: Lee TODAS las notas y textos relevantes del plano. Interpreta su
    significado para cuantificación.

Devuelve este JSON EXACTO (sin texto adicional):
{schema}
