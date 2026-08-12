#!/usr/bin/env python3
"""Contracts for the explanatory README architecture hero."""
from __future__ import annotations

import hashlib
import json
import re
import struct
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"
HERO = REPO / "docs" / "assets" / "readme-architecture.jpg"
HERO_CONTRACT = REPO / "docs" / "assets" / "readme-architecture.json"
OLD_PREVIEW = REPO / "docs" / "assets" / "preview.png"
SELECTED_TAGLINE = (
    "Design, route, secure, and operate agents across open-weight and hosted models."
)


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject ambiguous JSON contracts instead of accepting the last value."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def jpeg_dimensions(path: Path) -> tuple[int, int]:
    """Read JPEG dimensions without adding an image-library dependency."""
    data = path.read_bytes()
    if not data.startswith(b"\xff\xd8"):
        raise ValueError("asset is not a JPEG")

    offset = 2
    start_of_frame = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while offset + 3 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9}:
            continue
        if offset + 2 > len(data):
            break
        length = struct.unpack(">H", data[offset : offset + 2])[0]
        if marker in start_of_frame and offset + 7 <= len(data):
            height, width = struct.unpack(">HH", data[offset + 3 : offset + 7])
            return width, height
        if length < 2:
            break
        offset += length
    raise ValueError("JPEG dimensions were not found")


class ReadmeHeroTests(unittest.TestCase):
    def test_readme_uses_the_explanatory_architecture_hero(self) -> None:
        readme = README.read_text(encoding="utf-8")
        self.assertIn(f"**{SELECTED_TAGLINE}**", readme)
        image = re.search(r'<img\s+src="([^"]+)"\s+alt="([^"]+)"\s+width="820">', readme)
        self.assertIsNotNone(image)
        assert image is not None
        self.assertEqual(image.group(1), "docs/assets/readme-architecture.jpg")
        self.assertRegex(image.group(2), r"(?i)high-level.*request.*answer")
        self.assertNotRegex(image.group(2), r"(?i)five-layer architecture")
        self.assertNotIn("docs/assets/preview.png", readme)

    def test_visible_copy_and_light_theme_have_a_source_contract(self) -> None:
        contract = json.loads(
            HERO_CONTRACT.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
        self.assertEqual(contract["theme"], "light")
        self.assertEqual(
            contract["imageSha256"], hashlib.sha256(HERO.read_bytes()).hexdigest()
        )
        self.assertEqual(
            contract["verification"],
            "Exact image reviewed visually at full and 820px rendered widths",
        )
        self.assertEqual(contract["title"], "The Open-Weight Agent Stack")
        self.assertEqual(contract["subtitle"], SELECTED_TAGLINE)
        self.assertEqual(
            contract["bands"],
            [
                {"name": "EXPERIENCE", "detail": "Clients · API · Edge"},
                {
                    "name": "CONTROL PLANE",
                    "detail": "Identity · Gateway · Orchestrator",
                },
                {
                    "name": "GROUNDING & STATE",
                    "detail": "RAG · Memory · Tools via MCP",
                },
                {
                    "name": "INFERENCE",
                    "detail": "Router · Open-weight models · Serving",
                },
                {
                    "name": "FOUNDATIONS",
                    "detail": "Hardware · Security · Observability",
                },
            ],
        )
        self.assertEqual(contract["flow"], ["REQUEST", "ANSWER"])

        manual = (REPO / "MANUAL.md").read_text(encoding="utf-8")
        section_count = len(re.findall(r"^## \d+\.", manual, flags=re.MULTILINE))
        diagram_count = len(list((REPO / "diagrams" / "src").glob("*.mmd")))
        self.assertEqual(
            contract["stats"],
            [
                f"{section_count} SECTIONS",
                f"{diagram_count} DIAGRAMS",
                "SOURCE-LINKED CLAIMS",
            ],
        )

    def test_hero_is_a_readable_retina_asset_without_excess_weight(self) -> None:
        self.assertTrue(HERO.is_file())
        width, height = jpeg_dimensions(HERO)
        self.assertGreaterEqual(width, 1640)
        self.assertGreaterEqual(height, 900)
        self.assertLessEqual(abs((width / height) - (16 / 9)), 0.02)
        self.assertLessEqual(HERO.stat().st_size, 500_000)

    def test_stale_webpage_screenshot_is_removed(self) -> None:
        self.assertFalse(OLD_PREVIEW.exists())


if __name__ == "__main__":
    unittest.main()
