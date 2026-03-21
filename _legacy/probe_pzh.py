"""Probe PZH - output to file for full reading."""
path = r"c:\Users\chris\Documents\Dupla\presto_files\CTXI0000TRM.pzh"
out = r"c:\Users\chris\Documents\Dupla\pzh_probe_result.txt"

with open(path, "rb") as f:
    data = f.read()

lines = []
size = len(data)
lines.append(f"Size: {size:,} bytes ({size/1024/1024:.2f} MB)")

nulls = data.count(b"\x00")
lines.append(f"Null bytes: {nulls:,} ({nulls/size*100:.1f}%)")

for i in range(min(len(data), 5000)):
    if data[i] != 0:
        lines.append(f"First non-zero at byte {i}: {repr(data[i:i+80])}")
        break

keywords = [b"Presto", b"PRESTO", b"capitulo", b"partida", b"concepto",
            b"codigo", b"precio", b"unidad", b"medicion", b"Jet",
            b"Standard", b"Access", b"SQLite", b"TABLE", b"CREATE",
            b"PK\x03\x04", b"MDB", b"obra", b"OBRA",
            b"presupuesto", b"PRESUPUESTO", b"Cimentaci", b"Hormig",
            b"Muros", b"Puertas", b"Ventanas", b"Columnas",
            b"m2", b"m3", b"ud", b"ml", b"kg"]

lines.append("\n=== KEYWORDS ===")
for kw in keywords:
    positions = []
    start = 0
    while True:
        pos = data.find(kw, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 1
        if len(positions) > 5:
            break
    if positions:
        lines.append(f"\n  '{kw.decode('latin-1', errors='replace')}' found {len(positions)}x: {positions[:5]}")
        for p in positions[:3]:
            ctx = data[max(0,p-20):p+len(kw)+40]
            try:
                decoded = ctx.decode("latin-1")
                printable = "".join(c if c.isprintable() else "." for c in decoded)
            except:
                printable = repr(ctx)
            lines.append(f"    @{p}: {printable}")

# Data blocks
lines.append("\n=== DATA BLOCKS (non-null, >10 bytes) ===")
in_block = False
block_start = 0
blocks = []
for i in range(len(data)):
    if data[i] != 0 and not in_block:
        block_start = i
        in_block = True
    elif data[i] == 0 and in_block:
        block_len = i - block_start
        if block_len > 10:
            blocks.append((block_start, block_len))
        in_block = False

lines.append(f"Total data blocks: {len(blocks)}")
for start, length in blocks[:30]:
    preview = data[start:start+min(length, 100)]
    try:
        text = preview.decode("latin-1")
        printable = "".join(c if c.isprintable() else "." for c in text)
    except:
        printable = repr(preview)
    lines.append(f"  [{start:>8}] len={length:>6}: {printable[:100]}")

with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Output: {out}")
print(f"Blocks: {len(blocks)}")
