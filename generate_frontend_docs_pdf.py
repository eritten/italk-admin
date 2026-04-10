from pathlib import Path


PAGE_WIDTH = 612
PAGE_HEIGHT = 792
LEFT = 54
TOP = 740
FONT_SIZE = 11
LEADING = 15
BOTTOM = 54


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def wrap_line(text: str, width: int = 92) -> list[str]:
    if not text:
        return [""]
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def markdown_to_text_lines(markdown: str) -> list[str]:
    lines: list[str] = []
    in_code = False
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            in_code = not in_code
            lines.append("")
            continue
        if in_code:
            lines.append(f"    {line}")
            continue
        if line.startswith("# "):
            lines.append(line[2:].upper())
            lines.append("")
            continue
        if line.startswith("## "):
            lines.append(line[3:].upper())
            lines.append("")
            continue
        if line.startswith("### "):
            lines.append(line[4:])
            lines.append("")
            continue
        if line.startswith("- "):
            wrapped = wrap_line(f"- {line[2:]}")
            lines.extend(wrapped)
            continue
        if line.startswith("1. "):
            wrapped = wrap_line(line)
            lines.extend(wrapped)
            continue
        if not line:
            lines.append("")
            continue
        lines.extend(wrap_line(line))
    return lines


def build_page_stream(lines: list[str]) -> bytes:
    commands = ["BT", f"/F1 {FONT_SIZE} Tf", f"{LEFT} {TOP} Td"]
    first = True
    for line in lines:
        if first:
            commands.append(f"({escape_pdf_text(line)}) Tj")
            first = False
        else:
            commands.append(f"0 -{LEADING} Td")
            commands.append(f"({escape_pdf_text(line)}) Tj")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1", "replace")


def paginate(lines: list[str]) -> list[list[str]]:
    usable_height = TOP - BOTTOM
    max_lines = usable_height // LEADING
    pages = []
    current: list[str] = []
    for line in lines:
        current.append(line)
        if len(current) >= max_lines:
            pages.append(current)
            current = []
    if current:
        pages.append(current)
    return pages


def build_pdf(pages: list[list[str]], output_path: Path) -> None:
    objects: list[bytes] = []

    def add_object(data: bytes) -> int:
        objects.append(data)
        return len(objects)

    font_obj = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids = []
    content_ids = []

    for page_lines in pages:
        stream = build_page_stream(page_lines)
        content_obj = add_object(
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream"
        )
        content_ids.append(content_obj)
        page_obj = add_object(
            f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_obj} 0 R >> >> /Contents {content_obj} 0 R >>".encode("latin-1")
        )
        page_ids.append(page_obj)

    pages_kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    pages_obj = add_object(
        f"<< /Type /Pages /Kids [{pages_kids}] /Count {len(page_ids)} >>".encode("latin-1")
    )
    catalog_obj = add_object(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode("latin-1"))

    for page_id in page_ids:
        page_index = page_id - 1
        objects[page_index] = objects[page_index].replace(b"/Parent 0 0 R", f"/Parent {pages_obj} 0 R".encode("latin-1"))

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("latin-1"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("latin-1")
    )
    output_path.write_bytes(pdf)


def main() -> None:
    base = Path(__file__).resolve().parent
    markdown = (base / "FRONTEND_DEVELOPER_GUIDE.md").read_text(encoding="utf-8")
    pages = paginate(markdown_to_text_lines(markdown))
    build_pdf(pages, base / "FRONTEND_DEVELOPER_GUIDE.pdf")


if __name__ == "__main__":
    main()
