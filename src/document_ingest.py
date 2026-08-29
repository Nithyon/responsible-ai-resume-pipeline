from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

import pdfplumber
from PIL import Image
from pypdf import PdfReader


PARSER_VERSION = "layout-preserving-pdfplumber-1.0.0"
KNOWN_HEADINGS = {
    "summary", "objective", "profile", "research interests", "experience", "work experience",
    "professional experience", "research experience", "employment", "internships", "teaching experience",
    "education", "degrees", "secondary education", "tertiary education", "skills", "technical skills",
    "projects", "open source", "publications", "selected publications", "certificates", "certifications",
    "languages", "awards", "achievements", "fellowships & prizes", "grants & awards", "societies",
    "leadership", "service", "personal details", "career objective", "trainings given", "science communication",
}


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_") or "section"


def rounded_bbox(values: tuple[float, float, float, float] | list[float]) -> list[float]:
    return [round(float(value), 2) for value in values]


def extract_lines(page: Any) -> tuple[list[dict[str, Any]], float]:
    words = page.extract_words(
        use_text_flow=True,
        keep_blank_chars=False,
        x_tolerance=2,
        y_tolerance=3,
        extra_attrs=["fontname", "size"],
    )
    sizes = [float(word.get("size") or 0) for word in words if word.get("size")]
    body_size = median(sizes) if sizes else 10.0
    lines: list[list[dict[str, Any]]] = []
    for word in sorted(words, key=lambda item: (round(float(item["top"]), 1), float(item["x0"]))):
        if not lines or abs(float(word["top"]) - float(lines[-1][0]["top"])) > 3:
            lines.append([word])
        else:
            lines[-1].append(word)

    output: list[dict[str, Any]] = []
    for line_words in lines:
        line_words.sort(key=lambda item: float(item["x0"]))
        text = " ".join(str(word["text"]) for word in line_words).strip()
        text = re.sub(r"\s*\(cid:\d+\)", "", text).strip()
        if not text:
            continue
        font_sizes = [float(word.get("size") or body_size) for word in line_words]
        fonts = sorted({str(word.get("fontname") or "") for word in line_words})
        output.append({
            "text": text,
            "bbox": rounded_bbox((
                min(float(word["x0"]) for word in line_words),
                min(float(word["top"]) for word in line_words),
                max(float(word["x1"]) for word in line_words),
                max(float(word["bottom"]) for word in line_words),
            )),
            "font_size": round(max(font_sizes), 2),
            "font_names": fonts,
            "bold": any("bold" in font.casefold() for font in fonts),
        })
    return output, body_size


def heading_type(line: dict[str, Any], body_size: float) -> str | None:
    text = line["text"].strip().rstrip(":")
    normalized = re.sub(r"\s+", " ", text.casefold())
    if normalized in KNOWN_HEADINGS:
        return slug(normalized)
    words = text.split()
    letters = [character for character in text if character.isalpha()]
    uppercase_ratio = sum(character.isupper() for character in letters) / len(letters) if letters else 0
    if 1 <= len(words) <= 7 and uppercase_ratio >= 0.85 and (line["bold"] or line["font_size"] >= body_size):
        return slug(text)
    if 1 <= len(words) <= 6 and line["bold"] and line["font_size"] >= body_size + 1.5:
        return slug(text)
    return None


def nearest_text_blocks(block: dict[str, Any], text_blocks: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    top, bottom = block["bbox"][1], block["bbox"][3]
    ranked = sorted(
        text_blocks,
        key=lambda candidate: min(abs(candidate["bbox"][1] - bottom), abs(top - candidate["bbox"][3])),
    )
    return [candidate for candidate in ranked[:limit] if candidate.get("text")]


def ingest_pdf(pdf_path: Path, asset_root: Path) -> dict[str, Any]:
    source_bytes = pdf_path.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    document_id = f"doc_{source_hash[:16]}"
    asset_dir = asset_root / pdf_path.stem / "images"
    asset_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(pdf_path)

    all_blocks: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None

    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            page_number = page_index + 1
            page_id = f"{document_id}_page_{page_number}"
            line_items, body_size = extract_lines(page)
            provisional: list[dict[str, Any]] = []
            for line in line_items:
                provisional.append({**line, "type": "text"})

            plumber_images = list(page.images)
            pypdf_images = list(reader.pages[page_index].images)
            for image_index, (plumber_image, embedded) in enumerate(zip(plumber_images, pypdf_images), start=1):
                try:
                    pil_image: Image.Image = embedded.image
                    extension = (pil_image.format or "png").lower()
                    image_path = asset_dir / f"page_{page_number}_image_{image_index}.{extension}"
                    pil_image.save(image_path)
                    image_hash = hashlib.sha256(image_path.read_bytes()).hexdigest()
                    top = plumber_image.get("top", page.height - float(plumber_image.get("y1", page.height)))
                    bottom = plumber_image.get("bottom", page.height - float(plumber_image.get("y0", 0)))
                    provisional.append({
                        "type": "image",
                        "bbox": rounded_bbox((plumber_image.get("x0", 0), top, plumber_image.get("x1", 0), bottom)),
                        "text": "",
                        "image_id": f"img_{image_hash[:16]}",
                        "file_path": image_path.relative_to(asset_root.parent).as_posix(),
                        "sha256": image_hash,
                        "mime_type": Image.MIME.get(pil_image.format, "application/octet-stream"),
                        "width_px": pil_image.width,
                        "height_px": pil_image.height,
                    })
                except Exception as exc:
                    print(f"Skipped image {image_index} on page {page_number} of {pdf_path.name}: {exc}")

            try:
                found_tables = page.find_tables()
            except Exception:
                found_tables = []
            for table_index, table in enumerate(found_tables, start=1):
                rows = table.extract() or []
                cleaned_rows = [[cell or "" for cell in row] for row in rows]
                if not any(any(cell.strip() for cell in row) for row in cleaned_rows):
                    continue
                provisional.append({
                    "type": "table",
                    "bbox": rounded_bbox(table.bbox),
                    "text": "\n".join(" | ".join(row) for row in cleaned_rows),
                    "table_id": f"{document_id}_p{page_number}_table_{table_index}",
                    "rows": cleaned_rows,
                })

            provisional.sort(key=lambda item: (item["bbox"][1], item["bbox"][0], item["type"] != "image"))
            page_blocks: list[dict[str, Any]] = []
            for reading_order, item in enumerate(provisional, start=1):
                if item["type"] == "text":
                    normalized_heading = heading_type(item, body_size)
                    if normalized_heading:
                        section_id = f"{document_id}_section_{len(sections) + 1}"
                        current_section = {
                            "section_id": section_id,
                            "title": item["text"],
                            "normalized_type": normalized_heading,
                            "start_page": page_number,
                            "block_ids": [],
                        }
                        sections.append(current_section)
                        item["type"] = "heading"
                if current_section is None:
                    current_section = {
                        "section_id": f"{document_id}_section_1",
                        "title": "Document header",
                        "normalized_type": "header",
                        "start_page": page_number,
                        "block_ids": [],
                    }
                    sections.append(current_section)
                block_id = f"{page_id}_block_{reading_order}"
                block = {
                    **item,
                    "block_id": block_id,
                    "page_id": page_id,
                    "page_number": page_number,
                    "section_id": current_section["section_id"],
                    "reading_order": reading_order,
                }
                current_section["block_ids"].append(block_id)
                page_blocks.append(block)
                all_blocks.append(block)

            text_blocks = [block for block in page_blocks if block["type"] in {"text", "heading"}]
            for block in page_blocks:
                if block["type"] not in {"image", "table"}:
                    continue
                context_blocks = nearest_text_blocks(block, text_blocks)
                context = " | ".join(candidate["text"] for candidate in context_blocks)
                candidates_below = [
                    candidate for candidate in text_blocks
                    if 0 <= candidate["bbox"][1] - block["bbox"][3] <= 70
                ]
                caption = min(candidates_below, key=lambda candidate: candidate["bbox"][1], default={}).get("text", "")
                block["nearby_text"] = context
                block["caption"] = caption
                block["context_block_ids"] = [candidate["block_id"] for candidate in context_blocks]
                asset = {key: value for key, value in block.items() if key not in {"font_names", "font_size", "bold"}}
                (images if block["type"] == "image" else tables).append(asset)

            for link_index, link in enumerate(page.hyperlinks or [], start=1):
                links.append({
                    "link_id": f"{page_id}_link_{link_index}",
                    "page_id": page_id,
                    "page_number": page_number,
                    "uri": link.get("uri") or "",
                    "bbox": rounded_bbox((link.get("x0", 0), link.get("top", 0), link.get("x1", 0), link.get("bottom", 0))),
                })

            pages.append({
                "page_id": page_id,
                "page_number": page_number,
                "width": round(float(page.width), 2),
                "height": round(float(page.height), 2),
                "raw_text": page.extract_text(layout=True) or "",
                "block_ids": [block["block_id"] for block in page_blocks],
            })

    return {
        "document": {
            "document_id": document_id,
            "source_file": pdf_path.name,
            "source_path": str(pdf_path.resolve()),
            "source_sha256": source_hash,
            "page_count": len(pages),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "parser_version": PARSER_VERSION,
            "pdf_metadata": {key.lstrip("/"): str(value) for key, value in (reader.metadata or {}).items()},
        },
        "hierarchy": {"pages": pages, "sections": sections},
        "blocks": all_blocks,
        "assets": {"images": images, "tables": tables},
        "links": links,
        "statistics": {
            "pages": len(pages),
            "sections": len(sections),
            "blocks": len(all_blocks),
            "text_blocks": sum(block["type"] in {"text", "heading"} for block in all_blocks),
            "images": len(images),
            "tables": len(tables),
            "links": len(links),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Preserve PDF pages, hierarchy, layout blocks, images, tables, and links.")
    parser.add_argument("--input", type=Path, default=Path("data/pdf_samples"))
    parser.add_argument("--output", type=Path, default=Path("data/structured"))
    parser.add_argument("--assets", type=Path, default=Path("data/structured_assets"))
    args = parser.parse_args()
    files = [args.input] if args.input.is_file() else sorted(args.input.glob("*.pdf"))
    args.output.mkdir(parents=True, exist_ok=True)
    for path in files:
        result = ingest_pdf(path, args.assets)
        output_path = args.output / f"{path.stem}.document.json"
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        stats = result["statistics"]
        print(
            f"{path.name}: {stats['pages']} pages, {stats['sections']} sections, "
            f"{stats['blocks']} blocks, {stats['images']} images, {stats['tables']} tables"
        )


if __name__ == "__main__":
    main()
