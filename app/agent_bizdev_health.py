#!/usr/bin/env python3
"""Simple health server for agent-bizdev development."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"status": "healthy", "service": "agent-bizdev", "version": "dev"}
            self.wfile.write(json.dumps(response).encode())
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Agent BizDev Service</h1>")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress logs for health checks
        if "/health" not in args[0]:
            super().log_message(format, *args)

if __name__ == "__main__":
    server = HTTPServer(("", 8080), HealthHandler)
    print("Agent BizDev service starting on port 8080...")
    server.serve_forever()
