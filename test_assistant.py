import unittest
from datetime import date
from assistant import ROOT, FIELDS, NoteIndex, aggregate, analyze, load_csv, monday


def shipment(i, route, day, cost, q=1, distance=1, kind='Short'):
    origin, destination = route.split('-')
    return dict(shipment_id=str(i), origin=origin, destination=destination, shipment_date=day,
                freight_cost_inr=str(cost), quantity_tonnes=str(q), distance_km=str(distance), route_type=kind)


class Evaluation(unittest.TestCase):
    def test_week_boundaries(self):
        self.assertEqual(monday('2025-01-05'), date(2024, 12, 30))
        self.assertEqual(monday('2025-01-06'), date(2025, 1, 6))

    def test_ratio_of_sums(self):
        data = [shipment(1, 'A-B', '2025-01-01', 10), shipment(2, 'A-B', '2025-01-02', 180, q=9)]
        self.assertEqual(next(iter(aggregate(data).values()))['cost'], 19)

    def test_history_calendar_window_no_lookahead_peer_exclusion(self):
        data = [shipment(1, 'A-B', '2024-10-28', 999), shipment(2, 'A-B', '2024-12-30', 10),
                shipment(3, 'A-B', '2025-01-06', 20), shipment(4, 'C-D', '2025-01-06', 5),
                shipment(5, 'A-B', '2025-01-13', 999)]
        _, audit = analyze(data, [])
        row = next(r for r in audit if r['route'] == 'A-B' and r['week_of'] == '2025-01-06')
        self.assertEqual(row['history_baseline'], 10)
        self.assertEqual(row['history_weeks'], 1)
        self.assertEqual(row['peer_baseline'], 5)
        self.assertEqual(row['flagged'], 'Yes')

    def test_labeled_evidence_retrieval(self):
        index = NoteIndex(load_csv(ROOT / 'data/context_notes.csv'))
        cases = [
            ('Chennai-Bangalore', '2025-02-24', .30, 'N001'),
            ('Chennai-Bangalore', '2025-03-03', .30, 'N001'),
            ('Chennai-Bangalore', '2025-03-10', .30, None),
            ('Mumbai-Pune', '2025-02-24', .30, None),
            ('Ahmedabad-Mumbai', '2025-01-20', .30, 'N002'),
            ('Ahmedabad-Mumbai', '2025-01-27', .30, None),
            ('Mumbai-Pune', '2025-05-05', .06, 'N003'),
            ('Mumbai-Pune', '2025-05-05', .30, None),
            ('Mumbai-Pune', '2025-05-12', .06, None),
            ('Mumbai-Delhi', '2024-07-29', .30, None),
            ('Delhi-Jaipur', '2024-03-11', .30, None),
            ('Kolkata-Bhubaneswar', '2025-06-09', .30, None),
            ('Mumbai-Pune', '2025-09-22', .30, None),
            ('Mumbai-Pune', '2025-10-27', .30, None),
        ]
        for route, week, rise, expected in cases:
            with self.subTest(route=route, week=week, rise=rise):
                note = index.retrieve(route, date.fromisoformat(week), rise)
                self.assertEqual(note['note_id'] if note else None, expected)

    def test_full_data_contract_and_citations(self):
        rows, audit = analyze(load_csv(ROOT / 'data/shipment_records.csv'), load_csv(ROOT / 'data/context_notes.csv'))
        self.assertEqual(len(rows), 728)
        self.assertTrue(all(list(r) == FIELDS for r in rows))
        for r in rows:
            self.assertEqual(bool(r['matched_note_id']), r['flagged'] == 'No (justified)')
        # Modifying future shipments cannot alter earlier results.
        data = load_csv(ROOT / 'data/shipment_records.csv')
        early, _ = analyze([r for r in data if r['shipment_date'] < '2025-01-01'], load_csv(ROOT / 'data/context_notes.csv'))
        self.assertEqual([r for r in rows if r['week_of'] < '2024-12-30'], [r for r in early if r['week_of'] < '2024-12-30'])

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            aggregate([shipment(1, 'A-B', '2025-01-01', 2, q=0)])

    def test_threshold_explanation_and_validation(self):
        data = [shipment(1, 'A-B', '2025-01-06', 10), shipment(2, 'A-B', '2025-01-13', 12)]
        rows, _ = analyze(data, [], threshold=.10)
        self.assertEqual(rows[-1]['flagged'], 'Yes')
        self.assertIn('10%', rows[-1]['reason'])
        for bad in (-.1, float('nan'), float('inf')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                analyze(data, [], threshold=bad)

    def test_bad_rows_and_duplicate_notes(self):
        valid = shipment(1, 'A-B', '2025-01-06', 10)
        for update in ({'origin': ''}, {'freight_cost_inr': 'nan'}, {'quantity_tonnes': '1e308', 'distance_km': '1e308'}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                aggregate([{**valid, **update}])
        with self.assertRaisesRegex(ValueError, 'Missing shipment columns'):
            aggregate([{'shipment_id': '1'}])
        with self.assertRaisesRegex(ValueError, 'Duplicate shipment_id'):
            aggregate([valid, valid])
        notes = load_csv(ROOT / 'data/context_notes.csv')
        with self.assertRaisesRegex(ValueError, 'Duplicate note_id'):
            NoteIndex(notes + [notes[0]])

    def test_changed_positive_note_fails_closed(self):
        notes = load_csv(ROOT / 'data/context_notes.csv')
        notes[0]['note'] = 'No flood or higher costs occurred.'
        self.assertIsNone(NoteIndex(notes).retrieve('Chennai-Bangalore', date(2025, 2, 24), .30))

    def test_sample_rows_match_numeric_examples(self):
        rows, _ = analyze(load_csv(ROOT / 'data/shipment_records.csv'), load_csv(ROOT / 'data/context_notes.csv'))
        samples = {('Delhi-Jaipur', '2024-11-11'): ('+35.5%', '+21.0%', 'Yes', ''),
                   ('Ahmedabad-Mumbai', '2025-01-20'): ('+29.5%', '+22.5%', 'No (justified)', 'N002'),
                   ('Mumbai-Pune', '2025-09-15'): ('+9.2%', '+23.6%', 'Yes', '')}
        for r in rows:
            key = (r['route'], r['week_of'])
            if key in samples:
                own, peer, verdict, note = samples[key]
                self.assertTrue(r['vs_own_history'].startswith(own))
                self.assertTrue(r['vs_similar_routes'].startswith(peer))
                self.assertEqual((r['flagged'], r['matched_note_id']), (verdict, note))


if __name__ == '__main__':
    unittest.main(verbosity=2)
