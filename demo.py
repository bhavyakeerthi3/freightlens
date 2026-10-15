"""Local demo server. python demo.py --port 8000 (standard library only)."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from assistant import ROOT, run
from questions import answer_question

ASSETS = {'/': ('index.html', 'text/html; charset=utf-8'),
          '/app.css': ('app.css', 'text/css; charset=utf-8'),
          '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
          '/download/output.csv': ('results/output.csv', 'text/csv; charset=utf-8')}


class Handler(BaseHTTPRequestHandler):
    def respond(self, content, kind, status=200, download=False):
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        if download:
            self.send_header('Content-Disposition', 'attachment; filename="freight_analysis.csv"')
        self.end_headers()
        self.wfile.write(content)

    def json_response(self, data, status=200):
        self.respond(json.dumps(data, allow_nan=False).encode(), 'application/json; charset=utf-8', status)

    def do_GET(self):
        url = urlparse(self.path)
        try:
            if url.path in ASSETS:
                name, kind = ASSETS[url.path]
                self.respond((ROOT / name).read_bytes(), kind, download=url.path.startswith('/download/'))
            elif url.path == '/api/results':
                self.json_response(json.loads((ROOT / 'results/audit.json').read_text(encoding='utf-8')))
            elif url.path == '/api/summary':
                self.json_response(json.loads((ROOT / 'results/cost_log.json').read_text(encoding='utf-8')))
            elif url.path == '/api/notes':
                from assistant import load_csv
                self.json_response(load_csv(ROOT / 'data/context_notes.csv'))
            elif url.path == '/api/ask':
                question = parse_qs(url.query).get('q', [''])[0]
                if len(question) > 1000:
                    self.json_response({'error': 'Please keep questions under 1,000 characters.'}, 400)
                    return
                rows = json.loads((ROOT / 'results/audit.json').read_text(encoding='utf-8'))
                self.json_response(answer_question(question, rows))
            else:
                self.json_response({'error': 'Not found'}, 404)
        except (OSError, ValueError, KeyError):
            self.log_error('Unable to serve %s', url.path)
            self.json_response({'error': 'Analysis unavailable. Run python assistant.py and restart the demo.'}, 500)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    run(ROOT / 'data', ROOT / 'results')
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError as exc:
        parser.exit(1, f'Cannot start demo: {exc}. Try --port 8001.\n')
    print(f'Open http://127.0.0.1:{args.port} (Ctrl+C to stop)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
