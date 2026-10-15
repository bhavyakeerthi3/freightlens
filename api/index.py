"""Read-only Vercel function for the published sample-data dashboard."""
import csv
import json
import logging
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from questions import answer_question


class handler(BaseHTTPRequestHandler):
    def respond(self, payload, status=200):
        body = json.dumps(payload, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        endpoint = query.get('endpoint', [''])[0]
        try:
            if endpoint in ('results', 'summary'):
                name = 'audit.json' if endpoint == 'results' else 'cost_log.json'
                self.respond(json.loads((ROOT / 'results' / name).read_text(encoding='utf-8')))
            elif endpoint == 'notes':
                with (ROOT / 'data/context_notes.csv').open(encoding='utf-8-sig', newline='') as f:
                    self.respond(list(csv.DictReader(f)))
            elif endpoint == 'ask':
                question = query.get('q', [''])[0]
                if len(question) > 1000:
                    self.respond({'error': 'Please keep questions under 1,000 characters.'}, 400)
                    return
                rows = json.loads((ROOT / 'results/audit.json').read_text(encoding='utf-8'))
                self.respond(answer_question(question, rows))
            else:
                self.respond({'error': 'Not found'}, 404)
        except (OSError, ValueError, KeyError):
            logging.exception('Unable to serve freight endpoint %s', endpoint)
            self.respond({'error': 'Analysis temporarily unavailable. Please try again.'}, 500)
