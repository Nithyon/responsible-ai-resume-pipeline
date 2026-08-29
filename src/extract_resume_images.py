from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image
from pypdf import PdfReader


def image_metadata(path: Path, root: Path, kind: str, page: int) -> dict[str, Any]:
    data = path.read_bytes()
    with Image.open(path) as image:
        width, height = image.size
        mime_type = Image.MIME.get(image.format, "application/octet-stream")
    digest = hashlib.sha256(data).hexdigest()
    return {
        "image_id": f"img_{digest[:16]}",
        "kind": kind,
        "source_page": page,
        "file_name": path.name,
        "relative_path": path.relative_to(root).as_posix(),
        "sha256": digest,
        "mime_type": mime_type,
        "width": width,
        "height": height,
    }


def extract_images(pdf_path: Path, output_root: Path) -> list[dict[str, Any]]:
    destination = output_root / pdf_path.stem
    destination.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    reader = PdfReader(pdf_path)

    for page_number, page in enumerate(reader.pages, start=1):
        for index, embedded in enumerate(page.images, start=1):
            try:
                image = embedded.image
                if image.width < 120 or image.height < 120:
                    continue
                extension = (image.format or "png").lower()
                target = destination / f"embedded_p{page_number}_{index}.{extension}"
                image.save(target)
                records.append(image_metadata(target, output_root, "embedded", page_number))
            except Exception as exc:
                print(f"Skipped embedded image in {pdf_path.name} page {page_number}: {exc}")

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract embedded passport/profile images from resumes.")
    parser.add_argument("--input", type=Path, default=Path("data/pdf_samples"))
    parser.add_argument("--output", type=Path, default=Path("data/images"))
    parser.add_argument("--processed", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    total = 0
    for pdf_path in sorted(args.input.glob("*.pdf")):
        records = extract_images(pdf_path, args.output)
        json_path = args.processed / f"{pdf_path.stem}.json"
        if not json_path.exists():
            raise FileNotFoundError(f"Missing processed resume for {pdf_path.name}: {json_path}")
        resume = json.loads(json_path.read_text(encoding="utf-8"))
        resume["images"] = records
        json_path.write_text(json.dumps(resume, indent=2, ensure_ascii=False), encoding="utf-8")
        total += len(records)
        print(f"{pdf_path.name}: {len(records)} stored image record(s)")
    print(f"IMAGE EXTRACTION COMPLETE: {total} files stored under {args.output}")


if __name__ == "__main__":
    main()
