"""Script manual para inspeccionar AutoCAD via COM.

No define tests de pytest y no debe ejecutar nada al importarse.
"""

from pathlib import Path

__test__ = False


def build_report(doc) -> str:
    """Genera un reporte basico del documento activo de AutoCAD."""
    from cad_automation.config import classify_layer

    info: list[str] = []
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
    disc_count: dict[str, int] = {}
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
        except Exception as exc:
            info.append(f"  [{i}] Error: {exc}")

    return "\n".join(info)


def main(output_path: Path | None = None) -> Path:
    """Conecta a la instancia activa de AutoCAD y guarda un reporte."""
    import win32com.client

    acad = win32com.client.GetActiveObject("AutoCAD.Application")
    doc = acad.ActiveDocument

    report = build_report(doc)
    output_path = output_path or Path(__file__).resolve().parent / "dwg_analysis.txt"
    output_path.write_text(report, encoding="utf-8")
    print(f"Reporte guardado en: {output_path}")
    return output_path


if __name__ == "__main__":
    main()
