from pathlib import Path
from docx2pdf import convert

input_dir = Path("Belgeler")
output_dir = Path("Belgeler_PDF")
output_dir.mkdir(exist_ok=True)

for docx_file in input_dir.glob("*.docx"):
    output_path = output_dir / f"{docx_file.stem}.pdf"
    convert(str(docx_file), str(output_path))