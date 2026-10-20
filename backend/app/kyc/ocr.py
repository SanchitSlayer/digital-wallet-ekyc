import re
from dataclasses import dataclass
from difflib import SequenceMatcher

import pytesseract
from PIL import Image, ImageOps

# Tesseract is most accurate when letters are roughly 20 to 30 pixels tall; small phone crops are scaled up to get there.
_MIN_OCR_WIDTH = 1200

_LABELLED_ID_NUMBER = re.compile(r"\bID\s*(?:NO|NUMBER|#)?\s*[.:\-]?\s*((?=[A-Z0-9]*\d)[A-Z0-9]{8,12})\b", re.IGNORECASE)
_UNLABELLED_ID_NUMBER = re.compile(r"\b((?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])[A-Z0-9]{8,12})\b", re.IGNORECASE)
_NON_LETTERS = re.compile(r"[^A-Z ]+")


@dataclass(frozen=True)
class OcrResult:
    text: str
    id_number: str | None
    matched_name: str | None
    name_match_score: float


def _otsu_threshold(image: Image.Image) -> int:
    # Otsu's method picks the grey level that best separates dark text from light background,
    # so cards photographed under different lighting do not need a hand-tuned cutoff.
    histogram = image.histogram()
    total_pixels = sum(histogram)
    total_intensity = sum(level * count for level, count in enumerate(histogram))
    dark_pixels = 0
    dark_intensity = 0
    best_threshold = 0
    best_separation = 0.0
    for level, count in enumerate(histogram):
        dark_pixels += count
        light_pixels = total_pixels - dark_pixels
        if dark_pixels == 0:
            continue
        if light_pixels == 0:
            break
        dark_intensity += level * count
        dark_mean = dark_intensity / dark_pixels
        light_mean = (total_intensity - dark_intensity) / light_pixels
        separation = dark_pixels * light_pixels * (dark_mean - light_mean) ** 2
        if separation > best_separation:
            best_separation = separation
            best_threshold = level
    return best_threshold


def preprocess(image: Image.Image) -> Image.Image:
    grayscale = ImageOps.grayscale(ImageOps.exif_transpose(image))
    if grayscale.width < _MIN_OCR_WIDTH:
        scale = _MIN_OCR_WIDTH / grayscale.width
        grayscale = grayscale.resize((_MIN_OCR_WIDTH, round(grayscale.height * scale)), Image.Resampling.LANCZOS)
    threshold = _otsu_threshold(grayscale)
    return grayscale.point(lambda pixel: 255 if pixel > threshold else 0)


def extract_text(image: Image.Image) -> str:
    return pytesseract.image_to_string(image).strip()


def extract_id_number(text: str) -> str | None:
    match = _LABELLED_ID_NUMBER.search(text) or _UNLABELLED_ID_NUMBER.search(text)
    return match.group(1) if match else None


def _normalize_name(value: str) -> str:
    words = _NON_LETTERS.sub(" ", value.upper()).split()
    return " ".join(word for word in words if word != "NAME")


def _similarity(first: str, second: str) -> float:
    in_order = SequenceMatcher(None, first, second).ratio()
    # Comparing sorted words as well means "DOE JANE" on a card still matches "Jane Doe" at registration.
    sorted_words = SequenceMatcher(None, " ".join(sorted(first.split())), " ".join(sorted(second.split()))).ratio()
    return max(in_order, sorted_words)


def match_name(text: str, registered_name: str) -> tuple[str | None, float]:
    target = _normalize_name(registered_name)
    best_line: str | None = None
    best_score = 0.0
    for line in text.splitlines():
        candidate = _normalize_name(line)
        if not candidate:
            continue
        score = _similarity(candidate, target)
        if score > best_score:
            best_line, best_score = line.strip(), score
    return best_line, round(best_score * 100, 1)


def analyze_id_image(image: Image.Image, registered_name: str) -> OcrResult:
    text = extract_text(preprocess(image))
    matched_name, score = match_name(text, registered_name)
    return OcrResult(text=text, id_number=extract_id_number(text), matched_name=matched_name, name_match_score=score)
