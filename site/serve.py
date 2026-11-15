#!/usr/bin/env python3
"""Local server for Fancam Maker.

Sends COOP/COEP headers so the browser is cross-origin isolated, which lets
onnxruntime-web use several WASM threads (analysis runs much faster).

    python3 serve.py          -> http://localhost:8000
    python3 serve.py 9000     -> http://localhost:9000
"""
import http.server, os, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get('PORT', 8000))
os.chdir(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      '.mjs': 'text/javascript', '.wasm': 'application/wasm',
                      '.onnx': 'application/octet-stream'}

    def send_head(self):
        """Adds HTTP Range support so videos opened by URL can seek."""
        rng = self.headers.get('Range')
        path = self.translate_path(self.path)
        if not rng or not rng.startswith('bytes=') or not os.path.isfile(path):
            return super().send_head()
        size = os.path.getsize(path)
        a, _, b = rng[6:].split(',')[0].partition('-')
        try:
            if a:
                start, end = int(a), (int(b) if b else size - 1)
            else:
                start, end = max(0, size - int(b)), size - 1
        except ValueError:
            return super().send_head()
        if start >= size:
            self.send_error(416)
            return None
        end = min(end, size - 1)
        f = open(path, 'rb')
        f.seek(start)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        self._remaining = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        n = getattr(self, '_remaining', None)
        if n is None:
            return super().copyfile(source, outputfile)
        self._remaining = None
        while n > 0:
            chunk = source.read(min(65536, n))
            if not chunk:
                break
            try:
                outputfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                break
            n -= len(chunk)

    def end_headers(self):
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.send_header('Cache-Control', 'no-cache')
        if not self.headers.get('Range'):
            self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()


http.server.ThreadingHTTPServer.allow_reuse_address = True
print(f'Fancam Maker: http://localhost:{PORT}')
http.server.ThreadingHTTPServer(('', PORT), Handler).serve_forever()
