"""
Analisis profundo de DWG via COM - Extrae propiedades de TODOS los elementos
para presupuesto, agrupados por disciplina y capa.

Propiedades extraidas:
- Area (m2) para polylines cerradas, hatches, circulos
- Longitud (m) para lineas, polylines, arcos
- Conteo por tipo de entidad
- Bloques: nombre y cantidad (para puertas, ventanas, equipos, etc.)
- Textos: contenido (especificaciones)
"""

import win32com.client
import sys
import time
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, r"c:\Users\chris\Documents\Dupla")
from cad_automation.config import classify_layer

# ============================================================
# CONEXION
# ============================================================
print("Conectando a Civil 3D...")
acad = win32com.client.GetActiveObject("AutoCAD.Application")
doc = acad.ActiveDocument
msp = doc.ModelSpace
total = msp.Count

insunits = doc.GetVariable("INSUNITS")
print(f"Archivo: {doc.Name}")
print(f"Entidades: {total}")
print(f"INSUNITS: {insunits}")
print()

# ============================================================
# EXTRAER PROPIEDADES DE CADA ENTIDAD
# ============================================================

# Estructura: discipline -> layer -> tipo -> [propiedades]
data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
block_counts = defaultdict(lambda: defaultdict(int))  # disc -> block_name -> count
errors = 0
start = time.time()

print(f"Analizando {total} entidades...")

for i in range(total):
    # Progreso cada 2000
    if i % 2000 == 0 and i > 0:
        elapsed = time.time() - start
        pct = i / total * 100
        rate = i / elapsed
        eta = (total - i) / rate if rate > 0 else 0
        print(f"  [{pct:5.1f}%] {i}/{total} entidades | "
              f"{elapsed:.0f}s | ETA: {eta:.0f}s")

    try:
        ent = msp.Item(i)
        obj_name = ent.ObjectName  # AcDbLine, AcDbPolyline, etc.
        layer = ent.Layer
        disc = classify_layer(layer)

        props = {
            "type": obj_name,
            "area": 0.0,
            "length": 0.0,
            "closed": False,
        }

        # Area
        try:
            if hasattr(ent, "Area"):
                props["area"] = float(ent.Area)
                props["closed"] = True
        except Exception:
            pass

        # Length
        try:
            if hasattr(ent, "Length"):
                props["length"] = float(ent.Length)
        except Exception:
            pass

        # Bloques (INSERT) - puertas, ventanas, equipos
        if obj_name == "AcDbBlockReference":
            try:
                block_name = ent.Name
                props["block_name"] = block_name
                block_counts[disc.name][block_name] += 1
            except Exception:
                pass

        # Radio para circulos
        if obj_name == "AcDbCircle":
            try:
                props["radius"] = float(ent.Radius)
            except Exception:
                pass

        data[disc.name][layer][obj_name].append(props)

    except Exception:
        errors += 1

elapsed = time.time() - start
print(f"\nCompletado en {elapsed:.1f}s ({errors} errores)")

# ============================================================
# GENERAR REPORTE
# ============================================================

lines = []
lines.append("=" * 90)
lines.append("ANALISIS PROFUNDO DE DWG PARA PRESUPUESTO")
lines.append(f"Archivo: {doc.Name}")
lines.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lines.append(f"Unidades: {'Metros' if insunits == 6 else f'INSUNITS={insunits}'}")
lines.append(f"Total entidades analizadas: {total - errors}")
lines.append("=" * 90)

# Para cada disciplina
for disc_name in sorted(data.keys()):
    layers = data[disc_name]
    total_area = 0
    total_length = 0
    total_entities = 0

    disc_lines = []

    for layer_name in sorted(layers.keys()):
        types = layers[layer_name]
        layer_area = 0
        layer_length = 0
        layer_count = 0

        type_details = []
        for type_name, props_list in sorted(types.items(),
                                             key=lambda x: -len(x[1])):
            count = len(props_list)
            area_sum = sum(p["area"] for p in props_list)
            length_sum = sum(p["length"] for p in props_list)
            closed_count = sum(1 for p in props_list if p["closed"])

            layer_area += area_sum
            layer_length += length_sum
            layer_count += count

            # Simplificar nombre del tipo
            simple = type_name.replace("AcDb", "")

            detail = f"      {simple:<25} x{count:>5}"
            if area_sum > 0:
                detail += f"  | Area: {area_sum:>14.2f}"
                if closed_count > 0:
                    detail += f" ({closed_count} cerradas)"
            if length_sum > 0:
                detail += f"  | Long: {length_sum:>14.2f}"

            type_details.append(detail)

        total_area += layer_area
        total_length += layer_length
        total_entities += layer_count

        disc_lines.append(f"    CAPA: {layer_name}")
        disc_lines.append(f"      Entidades: {layer_count}  |  "
                         f"Area total: {layer_area:,.2f}  |  "
                         f"Longitud total: {layer_length:,.2f}")
        disc_lines.extend(type_details)
        disc_lines.append("")

    # Encabezado de disciplina
    lines.append("")
    lines.append("-" * 90)
    lines.append(f"DISCIPLINA: {disc_name}")
    lines.append(f"  Capas: {len(layers)}  |  "
                f"Entidades: {total_entities}  |  "
                f"Area total: {total_area:,.2f}  |  "
                f"Longitud total: {total_length:,.2f}")
    lines.append("-" * 90)
    lines.extend(disc_lines)

# Bloques (elementos de catalogo: puertas, ventanas, equipos)
lines.append("")
lines.append("=" * 90)
lines.append("BLOQUES POR DISCIPLINA (puertas, ventanas, equipos, simbolos)")
lines.append("=" * 90)
for disc_name in sorted(block_counts.keys()):
    blocks = block_counts[disc_name]
    if not blocks:
        continue
    lines.append(f"\n  [{disc_name}]")
    for block_name, count in sorted(blocks.items(), key=lambda x: -x[1]):
        lines.append(f"    {block_name:<50} x{count:>5}")

lines.append("")
lines.append("=" * 90)
lines.append("FIN DEL ANALISIS")
lines.append("=" * 90)

report = "\n".join(lines)

# Guardar
output_path = r"c:\Users\chris\Documents\Dupla\dwg_deep_analysis.txt"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(report)

print(f"\nReporte guardado: {output_path}")
print(f"Disciplinas: {len(data)}")
print(f"Si las unidades son Metros, las areas estan en m2 y las longitudes en m.")
