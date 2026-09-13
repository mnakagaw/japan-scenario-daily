"""Loopback-only preview of the generated public directory under its Pages path."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlsplit
from pathlib import Path

BASE = '/japan-scenario-daily'
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(Path(__file__).resolve().parent/'dist'),**kwargs)
    def do_GET(self):
        if not urlsplit(self.path).path.startswith(BASE+'/'):
            self.send_error(404); return
        self.path=self.path[len(BASE):]
        super().do_GET()

if __name__ == '__main__':
    print('Preview: http://127.0.0.1:8767/japan-scenario-daily/', flush=True)
    ThreadingHTTPServer(('127.0.0.1',8767),Handler).serve_forever()
