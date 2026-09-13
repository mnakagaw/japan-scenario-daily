"""Regression cases for same-day editions and incompatible comparison inputs."""
import copy
import unittest
from pathlib import Path
from editions import load_editions, latest_per_day, comparable, validate_supplements, route, validate_references
from build import display_chars
ROOT=Path(__file__).resolve().parent

class EditionChecks(unittest.TestCase):
    def setUp(self):
        self.records=load_editions(ROOT)
        self.original=self.records[0][1]
        self.target_index=next(i for i,(_,d) in enumerate(self.records) if d.get('edition_id')=='2026-09-13/155257')
        self.latest=self.records[self.target_index][1]
    def changed_records(self,change):
        records=copy.deepcopy(self.records)
        change(records[self.target_index][1])
        return records
    def test_next_day_cannot_skip_supplement(self):
        next_day=copy.deepcopy(self.latest)
        next_day.update(date='2026-09-14',cutoff_at='2026-09-14T15:40:00+09:00')
        next_day.pop('previous_day_reference')
        with self.assertRaisesRegex(AssertionError,'must be explicit'):
            validate_references(self.records,next_day)
        next_day['previous_day_reference']={'path':route(self.original)+'data.json'}
        with self.assertRaisesRegex(AssertionError,'last available edition'):
            validate_references(self.records,next_day)
        prior=[d for _,d in self.records if d['date']=='2026-09-13'][-1]
        next_day['previous_day_reference']={'path':route(prior)+'data.json'}
        validate_references(self.records,next_day)
    def test_only_last_edition_per_day(self):
        history=[d for _,d in self.records]
        selected=latest_per_day(history)
        self.assertEqual(len(selected),len({d['date'] for d in history}))
        self.assertEqual(selected[-1],self.records[-1][1])
        self.assertNotEqual(route(self.original),route(self.latest))
    def test_equivalent_offsets_are_comparable(self):
        candidate=copy.deepcopy(self.latest)
        candidate['deadline']='2026-11-04T13:59:59+09:00'
        self.assertIsNotNone(comparable(candidate,self.original,candidate['scenarios'][0]))
    def test_changed_question_needs_new_version(self):
        candidate=copy.deepcopy(self.latest)
        candidate['scenarios'][0]['target']='A different event'
        with self.assertRaisesRegex(AssertionError,'Definition changed'):
            comparable(candidate,self.original,candidate['scenarios'][0])
        candidate['scenarios'][0]['definition_version']+=1
        self.assertIsNone(comparable(candidate,self.original,candidate['scenarios'][0]))
    def test_same_day_is_not_a_previous_day(self):
        records=self.changed_records(lambda d:d.update(previous_day_reference=d['same_day_reference']))
        with self.assertRaises(AssertionError): validate_supplements(ROOT,records,display_chars)
    def test_pre_read_values_cannot_be_missing_delta(self):
        records=self.changed_records(lambda d:d['scenarios'][0].update(github_delta_pp=None))
        with self.assertRaisesRegex(AssertionError,'Incorrect supplement delta'):
            validate_supplements(ROOT,records,display_chars)
    def test_future_same_day_reference_rejected_with_offsets(self):
        records=self.changed_records(lambda d:d.update(cutoff_at='2026-09-13T01:00:00-05:00'))
        with self.assertRaises(AssertionError): validate_supplements(ROOT,records,display_chars)
    def test_wrong_reference_hash_rejected(self):
        records=self.changed_records(lambda d:d['same_day_reference'].update(sha256='0'*64))
        with self.assertRaisesRegex(AssertionError,'reference changed'):
            validate_supplements(ROOT,records,display_chars)

if __name__=='__main__': unittest.main()
