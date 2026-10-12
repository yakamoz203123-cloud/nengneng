import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'scripts/validate_page_manifest.py'


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(), 'missing manifest validator')
        spec = importlib.util.spec_from_file_location('page_manifest', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.validate = module.validate_page_manifest
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        (self.base / 'prompt.md').write_text('scene', encoding='utf-8')
        self.data = {'schema_version': 1, 'book_id': 'b01', 'age_band': '3-4', 'pages': [
            {'page': 1, 'text_version': 'v1', 'current_prompt_path': 'prompt.md',
             'current_image_path': None, 'characters_version': 'test-v1',
             'text_area': [10, 110, 120, 80],
             'props': [{'id': 'blocks', 'count': 3, 'location': 'floor',
                        'state': 'loose', 'change': 'introduced'}],
             'knowledge_check': {'status': 'pending', 'evidence': ''}}]}

    def test_planning_without_image(self):
        self.assertEqual([], self.validate(self.data, self.base))

    def test_completion_needs_image(self):
        self.assertTrue(self.validate(self.data, self.base, True))

    def complete(self):
        (self.base / 'new.png').write_bytes(b'asset')
        self.data['pages'][0]['current_image_path'] = 'new.png'
        self.data['pages'][0]['knowledge_check'] = {'status': 'passed', 'evidence': 'viewed page 1; exactly 3 blocks'}
        self.data['pages'][0].update({
            'previous_page_state': {'state_id': 'story_start', 'summary': 'The story has not begun.'},
            'current_page_entry': {'state_id': 'page-01-entry', 'summary': 'Three blocks are on the floor.'},
            'next_page_hook': {'state_id': 'story_end', 'summary': 'The single-page story is complete.'},
            'text_image_match': {'status': 'passed', 'evidence': 'Reviewed text and image for page 1.'},
            'continuity_review': {'status': 'passed', 'evidence': 'Reviewed the story boundaries for page 1.'},
        })

    def test_selected_new_asset_only(self):
        self.complete()
        (self.base / 'old.png').write_bytes(b'old')
        (self.base / 'page01-backup.png').write_bytes(b'backup')
        self.assertEqual([], self.validate(self.data, self.base, True))

    def test_no_fallback_when_selected_missing(self):
        self.complete()
        (self.base / 'new.png').unlink()
        (self.base / 'old.png').write_bytes(b'old')
        self.assertTrue(self.validate(self.data, self.base, True))

    def test_knowledge_must_pass_and_have_evidence(self):
        self.complete()
        for check in ({'status': 'pending', 'evidence': 'todo'}, {'status': 'failed', 'evidence': 'wrong'}, {'status': 'passed', 'evidence': ''}):
            with self.subTest(check=check):
                self.data['pages'][0]['knowledge_check'] = check
                self.assertTrue(self.validate(self.data, self.base, True))

    def test_planning_allows_pending_continuity_reviews(self):
        self.data['pages'][0].update({
            'previous_page_state': {'state_id': 'story_start', 'summary': 'The story has not begun.'},
            'current_page_entry': {'state_id': 'page-01-entry', 'summary': 'Three blocks are on the floor.'},
            'next_page_hook': {'state_id': 'story_end', 'summary': 'The single-page story is complete.'},
            'text_image_match': {'status': 'pending', 'evidence': ''},
            'continuity_review': {'status': 'pending', 'evidence': ''},
        })
        self.assertEqual([], self.validate(self.data, self.base))

    def test_completion_requires_all_continuity_records(self):
        self.complete()
        del self.data['pages'][0]['previous_page_state']
        del self.data['pages'][0]['current_page_entry']
        del self.data['pages'][0]['next_page_hook']
        del self.data['pages'][0]['text_image_match']
        del self.data['pages'][0]['continuity_review']
        errors = self.validate(self.data, self.base, True)
        for field in ('previous_page_state', 'current_page_entry', 'next_page_hook',
                      'text_image_match', 'continuity_review'):
            with self.subTest(field=field):
                self.assertTrue(any(f'pages[1].{field}' in error for error in errors), errors)

    def test_continuity_records_require_their_declared_shapes(self):
        self.data['pages'][0].update({
            'previous_page_state': {'state_id': '', 'summary': 'The story has not begun.'},
            'current_page_entry': {'state_id': 'page-01-entry', 'summary': ''},
            'next_page_hook': {'state_id': 'story_end'},
            'text_image_match': {'status': 'unknown', 'evidence': 1},
            'continuity_review': [],
        })
        errors = self.validate(self.data, self.base)
        for field in ('previous_page_state.state_id', 'current_page_entry.summary',
                      'next_page_hook.summary', 'text_image_match.status',
                      'text_image_match.evidence', 'continuity_review'):
            with self.subTest(field=field):
                self.assertTrue(any(f'pages[1].{field}' in error for error in errors), errors)

    def test_completion_requires_passed_continuity_reviews_with_evidence(self):
        self.complete()
        for field, review in (
            ('text_image_match', {'status': 'pending', 'evidence': 'still reviewing'}),
            ('continuity_review', {'status': 'failed', 'evidence': 'state mismatch'}),
            ('text_image_match', {'status': 'passed', 'evidence': ''}),
        ):
            with self.subTest(field=field, review=review):
                self.complete()
                self.data['pages'][0][field] = review
                errors = self.validate(self.data, self.base, True)
                self.assertTrue(any(f'pages[1].{field}' in error for error in errors), errors)

    def test_declared_null_continuity_records_are_invalid_in_planning_and_completion(self):
        fields = ('previous_page_state', 'current_page_entry', 'next_page_hook',
                  'text_image_match', 'continuity_review')
        for require_images in (False, True):
            with self.subTest(require_images=require_images):
                self.complete()
                for field in fields:
                    self.data['pages'][0][field] = None
                errors = self.validate(self.data, self.base, require_images)
                for field in fields:
                    with self.subTest(field=field):
                        self.assertIn(f'pages[1].{field}: expected an object', errors)

    def test_continuity_records_reject_extra_keys_in_planning_and_completion(self):
        fields = ('previous_page_state', 'current_page_entry', 'next_page_hook',
                  'text_image_match', 'continuity_review')
        for require_images in (False, True):
            with self.subTest(require_images=require_images):
                self.complete()
                for field in fields:
                    self.data['pages'][0][field]['unexpected'] = 'not part of the schema'
                errors = self.validate(self.data, self.base, require_images)
                for field in fields:
                    with self.subTest(field=field):
                        self.assertIn(f'pages[1].{field}: expected exactly the required fields', errors)

    def test_adjacent_hook_must_match_next_page_entry(self):
        self.complete()
        second_page = copy.deepcopy(self.data['pages'][0])
        second_page.update({
            'page': 2,
            'previous_page_state': {'state_id': 'page-01-entry', 'summary': 'Three blocks are on the floor.'},
            'current_page_entry': {'state_id': 'different-state', 'summary': 'The next scene begins differently.'},
            'next_page_hook': {'state_id': 'story_end', 'summary': 'The story is complete.'},
        })
        self.data['pages'].append(second_page)
        errors = self.validate(self.data, self.base, True)
        self.assertTrue(any('pages[1].next_page_hook.state_id' in error for error in errors), errors)

    def test_duplicate_or_gap_page(self):
        for number in (1, 3):
            data = copy.deepcopy(self.data)
            data['pages'].append(copy.deepcopy(data['pages'][0]))
            data['pages'][1]['page'] = number
            self.assertTrue(self.validate(data, self.base))

    def test_invalid_age(self):
        for age in ('3-6', None, '', ['3-4', '5-7']):
            with self.subTest(age=age):
                self.data['age_band'] = age
                self.assertTrue(self.validate(self.data, self.base))

    def test_selected_age_bands_in_planning_and_completion(self):
        planning = copy.deepcopy(self.data)
        for age in ('3-4', '5-7', '8-10'):
            with self.subTest(age=age):
                self.data = copy.deepcopy(planning)
                self.data['age_band'] = age
                self.assertEqual([], self.validate(self.data, self.base))
                self.complete()
                self.assertEqual([], self.validate(self.data, self.base, True))

    def test_legacy_age_band_remains_readable(self):
        self.data['age_band'] = '5-6'
        self.assertEqual([], self.validate(self.data, self.base))
        self.complete()
        self.assertEqual([], self.validate(self.data, self.base, True))

    def test_bad_types_and_counts(self):
        for value in (-1, True, 1.5, '3'):
            data = copy.deepcopy(self.data)
            data['pages'][0]['props'][0]['count'] = value
            self.assertTrue(self.validate(data, self.base))
        for data in (None, [], {'schema_version': True}, {'pages': 'pages'}):
            self.assertTrue(self.validate(data, self.base))

    def test_duplicate_prop_and_missing_record(self):
        data = copy.deepcopy(self.data)
        data['pages'][0]['props'].append(copy.deepcopy(data['pages'][0]['props'][0]))
        self.assertTrue(self.validate(data, self.base))
        for key in ('text_version', 'characters_version', 'text_area', 'current_prompt_path', 'knowledge_check'):
            data = copy.deepcopy(self.data)
            del data['pages'][0][key]
            self.assertTrue(self.validate(data, self.base))

    def test_out_of_range_coordinate_returns_error(self):
        self.data['pages'][0]['text_area'][0] = 10 ** 400
        self.assertTrue(self.validate(self.data, self.base))


if __name__ == '__main__':
    unittest.main()
