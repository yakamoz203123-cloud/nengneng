"""Validate final reading and booklet PDFs before publication or acceptance."""
from pathlib import Path
import re

import pymupdf as fitz

from impose_booklet import MM, booklet_pairs


DEFAULT_MINIMUM_PRINT_TEXT_SIZE_PT = 18.0
DIMENSION_TOLERANCE_PT = 0.05


def normal(text):
    return re.sub(r'\s+', '', text)


def minimum_print_text_size(layout):
    value = layout.get('minimum_print_text_size_pt', DEFAULT_MINIMUM_PRINT_TEXT_SIZE_PT)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        value = DEFAULT_MINIMUM_PRINT_TEXT_SIZE_PT
    return max(DEFAULT_MINIMUM_PRINT_TEXT_SIZE_PT, float(value))


def _open_pdf(path, label, errors):
    path = Path(path)
    if not path.is_file():
        errors.append(f'{label} PDF is missing')
        return None
    if path.stat().st_size == 0:
        errors.append(f'{label} PDF is empty')
        return None
    try:
        return fitz.open(path)
    except (fitz.FileDataError, OSError, RuntimeError, ValueError):
        errors.append(f'{label} PDF is unreadable')
        return None


def _text_sizes(page):
    return [
        span['size']
        for block in page.get_text('dict')['blocks']
        if block.get('type') == 0
        for line in block['lines']
        for span in line['spans']
        if span['text'].strip()
    ]


def validation_errors(reading_path, print_path, expected_page_texts, page_mm=(148, 210), minimum_print_text_size_pt=DEFAULT_MINIMUM_PRINT_TEXT_SIZE_PT):
    """Return deterministic defects found in final reading and booklet PDFs."""
    errors = []
    reading = _open_pdf(reading_path, 'reading', errors)
    printing = _open_pdf(print_path, 'print', errors)
    if reading is None or printing is None:
        if reading is not None:
            reading.close()
        if printing is not None:
            printing.close()
        return errors
    try:
        expected_page_texts = list(expected_page_texts)
        expected_pages = len(expected_page_texts)
        pairs = booklet_pairs(expected_pages)
        if len(reading) != expected_pages:
            errors.append(f'reading PDF page count: expected {expected_pages}, got {len(reading)}')
        if len(printing) != len(pairs):
            errors.append(f'print PDF page count: expected {len(pairs)}, got {len(printing)}')
        expected_width, expected_height = (float(value) * MM for value in page_mm)
        for index, page in enumerate(reading, 1):
            if abs(page.rect.width - expected_width) > DIMENSION_TOLERANCE_PT or abs(page.rect.height - expected_height) > DIMENSION_TOLERANCE_PT:
                errors.append(f'reading page {index}: expected A5 dimensions')
            if index <= expected_pages and normal(expected_page_texts[index - 1]) not in normal(page.get_text()):
                errors.append(f'reading page {index}: expected text is not extractable')
        for index, page in enumerate(printing, 1):
            if abs(page.rect.width - 297 * MM) > DIMENSION_TOLERANCE_PT or abs(page.rect.height - 210 * MM) > DIMENSION_TOLERANCE_PT:
                errors.append(f'print page {index}: expected landscape A4 dimensions')
            if index <= len(pairs):
                for side, page_number in enumerate(pairs[index - 1]):
                    clip = fitz.Rect(side * page.rect.width / 2, 0, (side + 1) * page.rect.width / 2, page.rect.height)
                    if normal(expected_page_texts[page_number - 1]) not in normal(page.get_text(clip=clip)):
                        errors.append(f'print page {index}: expected text for page {page_number} is not extractable')
            threshold = max(DEFAULT_MINIMUM_PRINT_TEXT_SIZE_PT, float(minimum_print_text_size_pt))
            for size in _text_sizes(page):
                if size < threshold:
                    errors.append(f'print page {index}: text size {size:.1f} pt is below {threshold:.1f} pt')
    finally:
        reading.close()
        printing.close()
    return errors


def validate_exports(reading_path, print_path, expected_page_texts, page_mm=(148, 210), minimum_print_text_size_pt=DEFAULT_MINIMUM_PRINT_TEXT_SIZE_PT):
    """Validate exports or raise ``ValueError`` without modifying either PDF."""
    errors = validation_errors(reading_path, print_path, expected_page_texts, page_mm, minimum_print_text_size_pt)
    if errors:
        raise ValueError('; '.join(errors))
    return {'reading_pages': len(expected_page_texts), 'print_sides': len(booklet_pairs(len(expected_page_texts)))}
