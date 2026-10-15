from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "data" / "sample_hld" / "sample_hld_content.txt"
target = ROOT / "data" / "sample_hld" / "sample_autosar_hld.pdf"
text = source.read_text(encoding="utf-8")
doc = fitz.open()
for block in text.split("\n\n"):
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(60, 60, 535, 760), block, fontsize=11, fontname="helv", lineheight=1.35)
doc.save(target)
doc.close()
print(f"Generated {target}")
