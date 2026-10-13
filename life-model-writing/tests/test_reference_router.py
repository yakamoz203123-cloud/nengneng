import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reference_router import (  # noqa: E402
    ReferenceRouteError,
    build_skill_context,
    load_routes,
)


class ReferenceRouterTests(unittest.TestCase):
    def _fixture(self, root: Path):
        (root / "references").mkdir()
        (root / "SKILL.md").write_text("SKILL RULES", encoding="utf-8")
        (root / "references" / "theory-a.md").write_text("THEORY A", encoding="utf-8")
        (root / "references" / "spoken-script-style.md").write_text(
            "SPOKEN", encoding="utf-8"
        )
        route_path = root / "routes.json"
        route_path.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "common": ["references/spoken-script-style.md"],
                    "cases": {"pair-01": ["references/theory-a.md"]},
                }
            ),
            encoding="utf-8",
        )
        return route_path

    def test_route_loads_common_and_case_specific_references_in_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            route_path = self._fixture(root)

            routes = load_routes(route_path, root)
            context, files = build_skill_context(root, routes, "pair-01")

            self.assertIn("SKILL RULES", context)
            self.assertIn("SPOKEN", context)
            self.assertIn("THEORY A", context)
            self.assertEqual(
                files,
                ["references/spoken-script-style.md", "references/theory-a.md"],
            )

    def test_unknown_case_route_fails_instead_of_falling_back_to_all_references(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            route_path = self._fixture(root)
            routes = load_routes(route_path, root)

            with self.assertRaises(ReferenceRouteError):
                build_skill_context(root, routes, "not-declared")

    def test_route_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "references").mkdir()
            (root / "SKILL.md").write_text("SKILL", encoding="utf-8")
            route_path = root / "routes.json"
            route_path.write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "common": ["../outside.md"],
                        "cases": {"pair-01": []},
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ReferenceRouteError):
                load_routes(route_path, root)


if __name__ == "__main__":
    unittest.main()
