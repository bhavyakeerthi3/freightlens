import csv
import io
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen
from assistant import ROOT, FIELDS, run
from demo import Handler


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run(ROOT / 'data', ROOT / 'results')
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_home_and_assets(self):
        for url, kind in [('/', 'text/html'), ('/app.css', 'text/css'), ('/app.js', 'text/javascript')]:
            with self.subTest(url=url), urlopen(self.base + url) as r:
                self.assertEqual(r.status, 200)
                self.assertIn(kind, r.headers['Content-Type'])
                self.assertTrue(r.read())

    def test_data_and_summary(self):
        rows = json.load(urlopen(self.base + '/api/results'))
        summary = json.load(urlopen(self.base + '/api/summary'))
        notes = json.load(urlopen(self.base + '/api/notes'))
        self.assertEqual((len(rows), summary['shipments'], len(notes)), (728, 2940, 10))
        self.assertEqual(summary['verdict_counts']['Yes'], 11)

    def test_csv_download(self):
        with urlopen(self.base + '/download/output.csv') as r:
            self.assertIn('attachment', r.headers['Content-Disposition'])
            reader = csv.DictReader(io.StringIO(r.read().decode()))
            self.assertEqual(reader.fieldnames, FIELDS)
            self.assertEqual(len(list(reader)), 728)

    def test_question_response(self):
        data = json.load(urlopen(self.base + '/api/ask?' + urlencode({'q': 'Chennai-Bangalore March 2025'})))
        self.assertEqual(data['matches'][0]['week_of'], '2025-03-10')
        self.assertIn('unexplained', data['answer'].lower() + data['matches'][0]['reason'].lower())

    def test_unknown_url_and_long_question(self):
        for path, status in [('/not-a-route', 404), ('/api/ask?' + urlencode({'q': 'x' * 1001}), 400)]:
            with self.subTest(path=path), self.assertRaises(HTTPError) as caught:
                urlopen(self.base + path)
            self.assertEqual(caught.exception.code, status)


if __name__ == '__main__':
    unittest.main()
