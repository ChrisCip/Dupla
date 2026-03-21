"""Test rapido COM - solo capas y info basica, sin iterar entidades."""
import win32com.client
import sys
sys.path.insert(0, r"c:\Users\chris\Documents\Dupla")
from cad_automation.config import classify_layer

acad = win32com.client.GetActiveObject("AutoCAD.Application")
doc = acad.ActiveDocument

info = []
info.append("=== DOCUMENTO DWG ===")
info.append(f"Nombre: {doc.Name}")
info.append(f"Capas: {doc.Layers.Count}")

msp_count = doc.ModelSpace.Count
info.append(f"ModelSpace: {msp_count} entidades")
info.append(f"Layouts: {doc.Layouts.Count}")

insunits = doc.GetVariable("INSUNITS")
info.append(f"INSUNITS: {insunits}")

info.append("")
info.append("=== CAPAS Y DISCIPLINAS ===")
disc_count = {}
for i in range(doc.Layers.Count):
    layer = doc.Layers.Item(i)
    disc = classify_layer(layer.Name)
    disc_count[disc.name] = disc_count.get(disc.name, 0) + 1
    info.append(f"  [{disc.name:>7}] {layer.Name}")

info.append("")
info.append("=== RESUMEN DISCIPLINAS ===")
for disc, count in sorted(disc_count.items()):
    info.append(f"  {disc}: {count} capas")

info.append("")
info.append("=== LAYOUTS ===")
for i in range(doc.Layouts.Count):
    layout = doc.Layouts.Item(i)
    info.append(f"  {layout.Name}")

info.append("")
info.append("=== PRIMERAS 10 ENTIDADES (tipo y capa) ===")
limit = min(msp_count, 10)
for i in range(limit):
    try:
        ent = doc.ModelSpace.Item(i)
        info.append(f"  [{i}] {ent.ObjectName} en capa '{ent.Layer}'")
    except Exception as e:
        info.append(f"  [{i}] Error: {e}")

report = "\n".join(info)
with open(r"c:\Users\chris\Documents\Dupla\dwg_analysis.txt", "w", encoding="utf-8") as f:
    f.write(report)
print("LISTO")
