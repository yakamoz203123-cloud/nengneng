import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "generation_queue.py"


def load_module():
    if not SCRIPT_PATH.exists():
        raise AssertionError(f"missing production queue script: {SCRIPT_PATH}")
    spec = importlib.util.spec_from_file_location("generation_queue_under_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GenerationQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.book = self.root / "book"
        self.queue = self.root / "queue.json"
        self._make_book()
        self.module = load_module()

    def tearDown(self):
        self.temp.cleanup()

    def _make_book(self, pages=3):
        (self.book / "prompts").mkdir(parents=True)
        (self.book / "characters" / "v1").mkdir(parents=True)
        (self.book / "characters" / "v1" / "production-reference.png").write_bytes(b"ref")
        (self.book / "story.md").write_text("完整故事：小朋友观察花环如何诞生。", encoding="utf-8")
        page_list = []
        for page in range(1, pages + 1):
            prompt_path = self.book / "prompts" / f"page-{page:02d}.md"
            prompt_path.write_text(f"第{page}页插画提示词", encoding="utf-8")
            page_list.append(
                {
                    "page": page,
                    "text_version": "v1",
                    "characters_version": "v1",
                    "character_reference_path": "characters/v1/production-reference.png",
                    "production_reference_path": "characters/v1/production-reference.png",
                    "current_prompt_path": f"prompts/page-{page:02d}.md",
                    "current_image_path": None,
                }
            )
        common = {"title": "测试绘本", "age_band": "5-7", "pages": page_list}
        (self.book / "page-manifest.json").write_text(json.dumps(common), encoding="utf-8")
        (self.book / "storyboard.json").write_text(json.dumps({"pages": page_list}), encoding="utf-8")
        (self.book / "layout.json").write_text(json.dumps({"pages": page_list}), encoding="utf-8")

    def _init(self, **kwargs):
        return self.module.init_queue(self.book, self.queue, **kwargs)

    def test_init_rejects_incomplete_plan_before_creating_queue(self):
        storyboard = json.loads((self.book / "storyboard.json").read_text(encoding="utf-8"))
        storyboard["pages"] = storyboard["pages"][:-1]
        (self.book / "storyboard.json").write_text(json.dumps(storyboard), encoding="utf-8")
        with self.assertRaises(ValueError):
            self._init()
        self.assertFalse(self.queue.exists())

    def test_init_creates_one_job_per_page_with_bounded_default(self):
        state = self._init()
        self.assertEqual(state["max_in_flight"], 2)
        self.assertEqual(len(state["jobs"]), 3)
        self.assertTrue(all(job["status"] == "pending" for job in state["jobs"]))
        self.assertEqual(len({job["output_path"] for job in state["jobs"]}), 3)
        self.assertTrue(all(job["request_fingerprint"] for job in state["jobs"]))

    def test_claim_enforces_max_in_flight_and_complete_releases_slot(self):
        self._init(max_in_flight=2)
        self.module.claim_job(self.queue, 1)
        self.module.claim_job(self.queue, 2)
        with self.assertRaises(RuntimeError):
            self.module.claim_job(self.queue, 3)
        output = self.book / "images" / "page-01.png"
        output.parent.mkdir()
        output.write_bytes(b"page-one")
        self.module.complete_job(self.queue, 1, output)
        claimed = self.module.claim_job(self.queue, 3)
        self.assertEqual(claimed["page"], 3)

    def test_claim_batch_is_atomic_and_bounded(self):
        self._init(max_in_flight=2)
        claimed = self.module.claim_batch(self.queue, [1, 2])
        self.assertEqual([job["page"] for job in claimed], [1, 2])
        with self.assertRaises(RuntimeError):
            self.module.claim_batch(self.queue, [3])
        state = json.loads(self.queue.read_text(encoding="utf-8"))
        self.assertEqual([job["status"] for job in state["jobs"]], ["running", "running", "pending"])

    def test_reinitialization_does_not_trust_changed_completed_output(self):
        self._init()
        self.module.claim_job(self.queue, 1)
        output = self.book / "images" / "page-01.png"
        output.parent.mkdir()
        output.write_bytes(b"accepted")
        self.module.complete_job(self.queue, 1, output)
        output.write_bytes(b"changed-after-acceptance")
        state = self._init()
        job = next(job for job in state["jobs"] if job["page"] == 1)
        self.assertEqual(job["status"], "pending")
        self.assertIsNone(job["output_sha256"])

    def test_failures_retry_then_become_terminal(self):
        self._init(max_attempts=2)
        self.module.claim_job(self.queue, 1)
        first = self.module.fail_job(self.queue, 1, "temporary tool failure")
        self.assertEqual(first["status"], "retryable")
        self.module.claim_job(self.queue, 1)
        second = self.module.fail_job(self.queue, 1, "same failure")
        self.assertEqual(second["status"], "failed")
        self.assertEqual(second["attempts"], 2)
        self.assertEqual(len(second["errors"]), 2)

    def test_resume_preserves_completed_pages_and_requeues_running_pages(self):
        self._init()
        self.module.claim_job(self.queue, 1)
        self.module.claim_job(self.queue, 2)
        output = self.book / "images" / "page-01.png"
        output.parent.mkdir()
        output.write_bytes(b"accepted")
        self.module.complete_job(self.queue, 1, output)
        state = self.module.resume_queue(self.queue)
        jobs = {job["page"]: job for job in state["jobs"]}
        self.assertEqual(jobs[1]["status"], "completed")
        self.assertEqual(jobs[2]["status"], "retryable")

    def test_reset_page_only_invalidates_selected_page_and_keeps_old_output(self):
        self._init()
        for page in (1, 2):
            self.module.claim_job(self.queue, page)
            output = self.book / "images" / f"page-{page:02d}.png"
            output.parent.mkdir(exist_ok=True)
            output.write_bytes(f"page-{page}".encode())
            self.module.complete_job(self.queue, page, output)
        state = self.module.reset_page(self.queue, 2, "用户修改第2页动作")
        jobs = {job["page"]: job for job in state["jobs"]}
        self.assertEqual(jobs[1]["status"], "completed")
        self.assertEqual(jobs[2]["status"], "pending")
        self.assertEqual(jobs[2]["revision"], 2)
        self.assertTrue(jobs[2]["previous_output_path"].endswith("page-02.png"))
        self.assertTrue((self.book / jobs[2]["previous_output_path"]).exists())
        self.assertNotEqual(jobs[2]["request_fingerprint"], jobs[1]["request_fingerprint"])

    def test_reinitialization_detects_existing_output_as_cache(self):
        (self.book / "images").mkdir()
        for page in range(1, 4):
            output = self.book / "images" / f"page-{page:02d}.png"
            output.write_bytes(f"cached-{page}".encode())
        manifest = json.loads((self.book / "page-manifest.json").read_text(encoding="utf-8"))
        for page in manifest["pages"]:
            page["current_image_path"] = f"images/page-{page['page']:02d}.png"
        (self.book / "page-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        state = self._init()
        self.assertTrue(all(job["status"] == "cached" for job in state["jobs"]))
        self.assertEqual(self.module.status(self.queue)["counts"]["cached"], 3)


if __name__ == "__main__":
    unittest.main()
