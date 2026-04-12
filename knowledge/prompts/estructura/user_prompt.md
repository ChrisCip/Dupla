ANALIZA este plano ESTRUCTURAL ({view_type}) del nivel: {level_name}

{methodology_block}DATOS DEL CAD (úsalos para verificar y complementar lo que ves):
{cad_hints}

INSTRUCCIONES DE EXTRACCIÓN ESTRUCTURAL:

1. ZAPATAS: Busca cuadro de zapatas. Lee CADA tipo (Z-1, Z-2, Z-A) con dimensiones
   (largo x ancho x profundidad). Cuenta cuántas hay de cada tipo. Si ves
   "Z-1: 1.50x1.50x0.40" eso es ancho=1.50m, largo=1.50m, profundidad=0.40m.

2. COLUMNAS: Busca cuadro de columnas. Lee CADA tipo (C-1, C-2, C-A, C-B) con
   sección (ancho x alto). Notaciones: "C-1 0.40x0.40" = section_width=0.40,
   section_height=0.40. Cuenta CADA columna individualmente en la planta.

3. VIGAS: Busca cuadro de vigas. Lee CADA tipo (V-1, V-2, VA) con sección.
   "V-1 0.30x0.60" = width=0.30, height=0.60. Mide longitudes entre ejes o
   deduce de cotas. Para vigas de amarre use "tie_beam".

4. LOSAS: Identifica tipo (maciza, nervada, prefabricada). Lee espesor:
   "e=0.20" o "losa e=0.12". Calcula área de la losa por zona o nivel.
   Para losas nervadas, identifica casetones y nervios si son visibles.

5. MUROS DE CORTE: Identifica muros estructurales en hormigón armado.
   Diferéncialos de muros de bloques. Lee espesor y longitud.
   Notación "MC-1" o "Muro de Corte" = shear_wall.

6. ESCALERAS: Tipo estructural (hormigón armado, metálica). Lee ancho,
   cantidad de tramos, espesor de losa de escalera.

7. ACERO DE REFUERZO: Si hay cuadro de refuerzo o detalles de armado:
   - Lee diámetros: 3/8", 1/2", 5/8", 3/4", 1"
   - Lee espaciamiento de estribos: @0.10, @0.15, @0.20
   - Nota grado del acero: Grado 40, Grado 60

8. DETALLES CONSTRUCTIVOS: Lee TODOS los detalles de conexiones,
   empotramientos, anclajes, juntas de construcción.

9. ESPECIFICACIONES: Busca notas de resistencia del hormigón (f'c=210, 250, 280 kg/cm²),
   recubrimiento mínimo, tipo de cemento, aditivos.

10. ANOTACIONES: Lee TODAS las notas estructurales, especificaciones generales,
    referencia a normativas (ACI-318, MOPC).

IMPORTANTE: Solo extrae elementos ESTRUCTURALES. Ignora acabados, puertas, ventanas,
instalaciones eléctricas/sanitarias. Esos son de otras disciplinas.

Devuelve este JSON EXACTO (sin texto adicional):
{schema}
