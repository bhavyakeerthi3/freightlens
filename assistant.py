"""Auditable, offline freight anomaly assistant. Python 3.10+, no dependencies."""
import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIELDS = ['route', 'week_of', 'cost_per_tonne_km', 'vs_own_history',
          'vs_similar_routes', 'flagged', 'matched_note_id', 'reason']


def monday(value):
    d = date.fromisoformat(value)
    return d - timedelta(days=d.weekday())


def load_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def aggregate(records):
    buckets = defaultdict(lambda: [0.0, 0.0, 0])
    seen = set()
    required = {'shipment_id', 'origin', 'destination', 'route_type', 'shipment_date',
                'quantity_tonnes', 'distance_km', 'freight_cost_inr'}
    for r in records:
        missing = required - r.keys()
        if missing:
            raise ValueError('Missing shipment columns: ' + ', '.join(sorted(missing)))
        if any(not str(r[k] or '').strip() for k in required):
            raise ValueError('Blank required shipment field in row: ' + str(r.get('shipment_id')))
        if r['shipment_id'] in seen:
            raise ValueError('Duplicate shipment_id: ' + r['shipment_id'])
        seen.add(r['shipment_id'])
        q, d, c = (float(r[k]) for k in ('quantity_tonnes', 'distance_km', 'freight_cost_inr'))
        if not all(math.isfinite(v) for v in (q, d, c)) or q <= 0 or d <= 0 or c < 0:
            raise ValueError('Invalid numeric shipment: ' + r['shipment_id'])
        if r['route_type'] not in ('Short', 'Medium', 'Long'):
            raise ValueError('Unknown route_type')
        if not math.isfinite(q * d) or q * d == 0:
            raise ValueError('Invalid tonne-km exposure: ' + r['shipment_id'])
        key = (r['origin'] + '-' + r['destination'], r['route_type'], monday(r['shipment_date']))
        b = buckets[key]
        b[0] += c
        b[1] += q * d
        b[2] += 1
    return {k: {'cost': v[0] / v[1], 'shipments': v[2]} for k, v in buckets.items()}


class NoteIndex:
    """Small TF-IDF vector index; eligibility gates precede similarity ranking.

    Reviewed evidence annotations are deliberately explicit: free text is never
    allowed to invent a positive impact or an indefinite validity period.
    """
    WINDOWS = {
        'N001': ('2025-02-24', '2025-03-08', None),
        'N002': ('2025-01-20', '2025-01-26', None),
        'N003': ('2025-05-05', '2025-05-11', 0.07),
    }

    def __init__(self, notes):
        seen = set()
        for n in notes:
            if not {'note_id', 'date', 'applies_to', 'note'} <= n.keys():
                raise ValueError('Missing required note columns')
            if n['note_id'] in seen:
                raise ValueError('Duplicate note_id: ' + n['note_id'])
            seen.add(n['note_id'])
            date.fromisoformat(n['date'])
        self.notes = notes
        self.reviewed = json.loads((ROOT / 'reviewed_evidence.json').read_text(encoding='utf-8'))
        self.docs = [Counter(self.tokens(n['applies_to'] + ' ' + n['note'])) for n in notes]
        self.idf = {t: math.log((1 + len(notes)) / (1 + sum(t in d for d in self.docs))) + 1
                    for d in self.docs for t in d}

    @staticmethod
    def tokens(s):
        return re.findall(r'[a-z]+', s.lower())

    def score(self, query, doc):
        q = Counter(self.tokens(query))
        dot = sum(q[t] * doc[t] * self.idf.get(t, 1)**2 for t in q)
        a = math.sqrt(sum((v * self.idf.get(t, 1))**2 for t, v in q.items()))
        b = math.sqrt(sum((v * self.idf[t])**2 for t, v in doc.items()))
        return dot / (a * b) if a * b else 0

    def retrieve(self, route, week, rise):
        matches = []
        for n, doc in zip(self.notes, self.docs):
            window = self.WINDOWS.get(n['note_id'])
            if not window or n != self.reviewed.get(n['note_id']) or n['applies_to'] not in (route, 'All Routes'):
                continue
            start, end, cap = window
            # Require evidence published by the week's end and overlapping it.
            if date.fromisoformat(n['date']) > week + timedelta(days=6):
                continue
            if week > date.fromisoformat(end) or week + timedelta(days=6) < date.fromisoformat(start):
                continue
            # A 5-7% diesel increase cannot fully explain a 20%+ route spike.
            if cap is not None and (rise is None or rise > cap):
                continue
            matches.append((self.score(route + ' freight cost increase surcharge disruption', doc), n['note_id'], n))
        return sorted(matches, key=lambda x: (-x[0], x[1]))[0][2] if matches else None


def analyze(records, notes, threshold=0.20):
    if not math.isfinite(threshold) or threshold < 0:
        raise ValueError('Threshold must be a finite, nonnegative fraction')
    threshold_text = f'{threshold * 100:g}%'
    weekly = aggregate(records)
    index = NoteIndex(notes)
    result, audit = [], []
    for (route, kind, week), values in sorted(weekly.items()):
        cost = values['cost']
        prior = [(w, v['cost']) for (r, t, w), v in weekly.items()
                 if r == route and t == kind and week - timedelta(weeks=8) <= w < week]
        history = sum(c for _, c in prior) / len(prior) if prior else None
        peers = [v['cost'] for (r, t, w), v in weekly.items() if r != route and t == kind and w == week]
        peer = sum(peers) / len(peers) if peers else None
        own_delta = cost / history - 1 if history else None
        peer_delta = cost / peer - 1 if peer else None
        # Compare against the most recent observed week; first observations cannot establish a rise.
        older = [(w, v['cost']) for (r, t, w), v in weekly.items() if r == route and t == kind and w < week]
        previous = max(older)[1] if older else None
        rising = previous is not None and cost > previous
        candidate = rising and any(x is not None and x > threshold for x in (own_delta, peer_delta))
        note = index.retrieve(route, week, own_delta) if candidate else None
        verdict = 'No (justified)' if note else 'Yes' if candidate else 'No'
        if note:
            start, end, _ = index.WINDOWS[note['note_id']]
            reason = (f"Justified by note {note['note_id']} dated {note['date']} (applicable {start} to {end}): "
                      + note['note'] + ' Evidence supports a cost impact; it does not prove the full increase is reasonable.')
        elif candidate:
            reason = f'Unexplained: cost rose from the prior observed week and exceeded the {threshold_text} history or peer threshold. No applicable cost-increasing note supports this rise; review required.'
        else:
            reason = 'No alert: ' + ('no prior week establishes a rise.' if previous is None else
                     'cost did not rise from the prior observed week.' if not rising else
                     f'neither available baseline was exceeded by more than {threshold_text}.')
        if len(prior) < 8:
            reason += f' History uses {len(prior)} available prior weeks in the trailing 8-week window.'
        result.append(dict(zip(FIELDS, [route, week.isoformat(), f'{cost:.6f}',
            f'{own_delta:+.1%} vs this route\'s past average' if own_delta is not None else 'N/A',
            f'{peer_delta:+.1%} vs similar-length routes this week' if peer_delta is not None else 'N/A',
            verdict, note['note_id'] if note else '', reason])))
        audit.append({'route': route, 'route_type': kind, 'week_of': week.isoformat(),
                      'cost_per_tonne_km': cost, 'history_baseline': history, 'history_weeks': len(prior),
                      'peer_baseline': peer, 'peer_routes': len(peers), 'previous_cost': previous,
                      'own_delta': own_delta, 'peer_delta': peer_delta, 'candidate': candidate,
                      'flagged': verdict, 'matched_note_id': note['note_id'] if note else '',
                      'reason': reason, 'evidence': dict(note) if note else None,
                      'evidence_window': list(index.WINDOWS[note['note_id']][:2]) if note else None,
                      'shipments': values['shipments']})
    return result, audit


def run(data, out):
    out.mkdir(parents=True, exist_ok=True)
    records = load_csv(data / 'shipment_records.csv')
    notes = load_csv(data / 'context_notes.csv')
    rows, audit = analyze(records, notes)
    with open(out / 'output.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (out / 'audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    log = {'shipments': len(records), 'route_weeks': len(rows), 'verdict_counts': dict(Counter(r['flagged'] for r in rows)),
           'model': 'None: deterministic TF-IDF retrieval and evidence templates', 'llm_calls': 0,
           'input_tokens': 0, 'output_tokens': 0, 'estimated_cost_usd': 0,
           'pricing_basis': 'No model API or paid service used; published model rate not applicable.',
           'output_sha256': hashlib.sha256((out / 'output.csv').read_bytes()).hexdigest()}
    (out / 'cost_log.json').write_text(json.dumps(log, indent=2), encoding='utf-8')
    return log


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'data')
    parser.add_argument('--out', type=Path, default=ROOT / 'results')
    args = parser.parse_args()
    print(json.dumps(run(args.data, args.out), indent=2))
