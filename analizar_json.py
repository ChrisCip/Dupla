import json

with open("resultados_model_derivative.json") as f:
    data = json.load(f)

objects = data["views"][0]["objects"]

# Layers que nos importan para presupuesto
target_layers = [
    "A-WALL", "A-DOOR", "A-GLAZ", "A-FLOR", 
    "S-COLS", "S-BEAM", "E-ELEC-FIXT", "P-SANR-FIXT",
    "00-MEDICION", "A-FLOR-PATT", "A-DOOR-GLAZ"
]

for layer in target_layers:
    print(f"\n{'='*60}")
    print(f"LAYER: {layer}")
    print(f"{'='*60}")
    count: int = 0
    for obj in objects:
        props = obj.get("properties", {})
        general = props.get("General", {})
        if general.get("Layer") == layer and count < 3:
            print(f"\n  Name: {obj.get('name')}")
            print(f"  Type: {general.get('Name ', 'N/A')}")
            # Print ALL property groups
            for group_name, group_props in props.items():
                if group_name != "General":
                    print(f"  [{group_name}]")
                    for k, v in group_props.items():
                        print(f"    {k}: {v}")
            count += 1  # type: ignore
    if count == 0:
        print("  (no objects found)")