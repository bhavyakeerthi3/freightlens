import unittest
from assistant import ROOT, analyze, load_csv
from questions import answer_question


class QuestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.rows = analyze(load_csv(ROOT / 'data/shipment_records.csv'), load_csv(ROOT / 'data/context_notes.csv'))

    def test_month_question_never_reuses_expired_flood_note(self):
        result = answer_question('Why did Chennai–Bangalore get pricier in March 2025?', self.rows)
        self.assertEqual([r['week_of'] for r in result['matches']], ['2025-03-10'])
        self.assertNotIn('N001', result['answer'])
        self.assertIn('No applicable cost-increasing note', result['answer'])

    def test_festival_answer_cites_exact_source(self):
        result = answer_question('Why Ahmedabad Mumbai in January 2025?', self.rows)
        self.assertEqual(result['matches'][0]['matched_note_id'], 'N002')
        self.assertIn('limited truck availability', result['answer'])

    def test_iso_date_maps_sunday_to_monday(self):
        result = answer_question('Chennai-Bangalore 2025-03-02', self.rows)
        self.assertEqual(result['filters']['week'], '2025-02-24')
        self.assertEqual(result['matches'][0]['matched_note_id'], 'N001')

    def test_guidance_empty_and_ambiguous(self):
        for q, expected in [('', 'Ask about a route'), ('anything', 'Include a route'),
                            ('Chennai-Bangalore Mumbai-Pune', 'one route'),
                            ('Chennai-Bangalore March April 2025', 'one month'),
                            ('Mumbai-Pune 2025-02-31', 'invalid'),
                            ('Mumbai-Pune March 2029', 'no observed')]:
            with self.subTest(q=q):
                self.assertIn(expected, answer_question(q, self.rows)['answer'])

    def test_missing_year_is_explicit(self):
        self.assertIn('all available years', answer_question('Chennai-Bangalore March', self.rows)['answer'])

    def test_verdict_summary(self):
        result = answer_question('Show justified alerts in 2025', self.rows)
        self.assertEqual(len(result['matches']), 2)
        self.assertTrue(all(r['flagged'] == 'No (justified)' for r in result['matches']))


if __name__ == '__main__':
    unittest.main()
