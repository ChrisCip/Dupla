import json, os, glob
from pathlib import Path

# Load BC3 dump
dump_dir = Path(r"c:\Users\chris\Documents\Dupla\analysis_output\dump")
bc3_partidas = json.loads((dump_dir / "partidas_bc3.json").read_text(encoding="utf-8"))

# Create a dictionary for quick lookup of BC3 data
bc3_dict = {p["code"]: p for p in bc3_partidas}

# Load latest output JSON
files = glob.glob(r"c:\Users\chris\Documents\Dupla\analysis_output\ANALISIS_INTEGRAL_*.json")
latest = max(files, key=os.path.getctime)
output_data = json.loads(Path(latest).read_text(encoding="utf-8"))

total_items_generated = output_data.get("total_items", 0)
if total_items_generated == 0:
    print("No items generated to compare.")
    exit()

exact_code_matches = 0
exact_price_matches = 0
exact_unit_matches = 0
description_similarity_high = 0

print("="*60)
print(f"  COMPARACIÓN DE PRECISIÓN: OUTPUT vs BC3 ORIGINAL")
print(f"  Archivo evaluado: {os.path.basename(latest)}")
print("="*60)

for chapter in output_data.get("budget_chapters", []):
    for item in chapter.get("items", []):
        code = item.get("presto_code", "")
        # Check if code exists in BC3
        if code in bc3_dict:
            exact_code_matches += 1
            bc3_item = bc3_dict[code]
            
            # Check price match
            out_price = float(item.get("unit_price", 0))
            bc3_price = float(bc3_item.get("price", 0))
            if abs(out_price - bc3_price) < 0.01:
                exact_price_matches += 1
                
            # Check unit match
            out_unit = item.get("unit", "").lower()
            bc3_unit = bc3_item.get("unit", "").lower()
            if out_unit == bc3_unit or (out_unit in ["m2", "m²"] and bc3_unit in ["m2", "m²"]):
                exact_unit_matches += 1
                
            # Description similarity (naive word overlap)
            out_words = set(item.get("description", "").lower().split())
            bc3_words = set(bc3_item.get("summary", "").lower().split())
            if len(out_words) > 0 and len(out_words.intersection(bc3_words)) / len(out_words) > 0.5:
                description_similarity_high += 1
        else:
            # Code was hallucinated or came from XLS instead of BC3
            pass

# Calculate percentages
code_precision = (exact_code_matches / total_items_generated) * 100
price_precision = (exact_price_matches / total_items_generated) * 100
unit_precision = (exact_unit_matches / total_items_generated) * 100
desc_precision = (description_similarity_high / total_items_generated) * 100

print(f"\n  MÉTRICAS DE PRECISIÓN (Muestra: {total_items_generated} partidas generadas)")
print(f"  --------------------------------------------------")
print(f"  Precisión de Códigos:       {code_precision:>6.1f}%  ({exact_code_matches}/{total_items_generated})")
print(f"  Precisión de Precios:       {price_precision:>6.1f}%  ({exact_price_matches}/{total_items_generated})")
print(f"  Precisión de Unidades:      {unit_precision:>6.1f}%  ({exact_unit_matches}/{total_items_generated})")
print(f"  Similitud de Descripciones: {desc_precision:>6.1f}%  ({description_similarity_high}/{total_items_generated})")

overall_score = (code_precision + price_precision + unit_precision + desc_precision) / 4
print(f"\n  >> PUNTAJE DE PRECISIÓN GLOBAL: {overall_score:.1f}% <<")

if code_precision < 100:
    print("\n  [INFO] El porcentaje restante corresponde a códigos estimados/alucinados por la IA o extraídos del Excel de referencia (PRES.xlsx) que no existen idénticos en el BC3.")
