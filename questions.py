"""Grounded structured question answering. No model calls or invented facts."""
import calendar
import re
from datetime import date, timedelta


def normalize(value):
    return ' '.join(re.findall(r'[a-z0-9]+', value.lower()))


def answer_question(question, rows):
    """Recognize routes, month/year or ISO week; filter by Monday week_of."""
    if not question.strip():
        return {'answer': 'Ask about a route and optional month, year, or Monday date.', 'matches': [], 'filters': {}}
    routes = sorted({r['route'] for r in rows})
    q = normalize(question)
    selected = [route for route in routes if normalize(route) in q]
    if len(selected) > 1:
        return {'answer': 'Please ask about one route at a time.', 'matches': [], 'filters': {}}
    years = {int(y) for y in re.findall(r'\b(20\d{2})\b', question)}
    months = {i for i in range(1, 13) if re.search(r'\b(' + calendar.month_name[i].lower() + '|' + calendar.month_abbr[i].lower() + r')\b', question.lower())}
    iso_dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', question)
    if len(years) > 1 or len(months) > 1 or len(iso_dates) > 1:
        return {'answer': 'Use one month/year or one ISO date per question.', 'matches': [], 'filters': {}}
    week = None
    if iso_dates:
        try:
            d = date.fromisoformat(iso_dates[0])
            week = (d - timedelta(days=d.weekday())).isoformat()
        except ValueError:
            return {'answer': 'That date is invalid. Use YYYY-MM-DD.', 'matches': [], 'filters': {}}
    month = next(iter(months), None)
    year = next(iter(years), None)
    filters = {'route': selected[0] if selected else None, 'month': month, 'year': year, 'week': week}
    if not selected and not any(t in q.split() for t in ('overview', 'summary', 'alerts', 'unexplained', 'justified')):
        return {'answer': 'Include a route name or ask for an alert summary. Available routes: ' + ', '.join(routes) + '.', 'matches': [], 'filters': filters}
    scoped = [r for r in rows if (not selected or r['route'] == selected[0])
              and (not week or r['week_of'] == week)
              and (not month or int(r['week_of'][5:7]) == month)
              and (not year or int(r['week_of'][:4]) == year)]
    candidates = [r for r in scoped if r['candidate']]
    if 'unexplained' in q.split():
        candidates = [r for r in candidates if r['flagged'] == 'Yes']
    elif 'justified' in q.split():
        candidates = [r for r in candidates if r['flagged'] == 'No (justified)']
    label = selected[0] if selected else 'All routes'
    if not scoped:
        text = f'{label}: no observed route-weeks match that period.'
    elif not candidates:
        text = f'{label}: {len(scoped)} observed weeks, no candidate rises matching this question under the configured policy. This does not prove every rate is reasonable.'
    else:
        facts = []
        for r in candidates:
            own = f"{r['own_delta']:+.1%} versus history" if r['own_delta'] is not None else 'history unavailable'
            peer = f"{r['peer_delta']:+.1%} versus peers" if r['peer_delta'] is not None else 'peers unavailable'
            evidence = ('Supported by ' + r['matched_note_id'] + ': ' + r['evidence']['note']) if r.get('evidence') else 'No applicable cost-increasing note supports this rise.'
            facts.append(f"{r['week_of']} ({r['route']}): INR {r['cost_per_tonne_km']:.4f}/tonne-km, {own}, {peer}. {r['flagged']}. {evidence}")
        noun = 'rise' if len(candidates) == 1 else 'rises'
        text = f'{label}: {len(candidates)} candidate {noun} in {len(scoped)} observed weeks.\n\n' + '\n\n'.join(facts)
    if month and not year:
        text += '\n\nNo year specified: this month includes all available years.'
    return {'answer': text, 'matches': candidates, 'filters': filters}
