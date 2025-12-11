#!/usr/bin/env python3
"""
Simple HTTP server to display incoming POST requests and their payloads.
Useful for testing MQTT subscriber mode or HTTP bridge.

Usage:
    python3 test_server.py [port]
    
Default port: 8080
"""

import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Override to customize logging"""
        pass
    
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        # Print timestamp and request info
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{'='*80}")
        print(f"[{timestamp}] POST {self.path}")
        print(f"{'='*80}")
        
        # Print headers
        print("\nHeaders:")
        for header, value in self.headers.items():
            print(f"  {header}: {value}")
        
        # Print body
        print("\nBody:")
        try:
            # Try to parse as JSON for pretty printing
            if self.headers.get('Content-Type', '').startswith('application/json'):
                data = json.loads(body)
                print(json.dumps(data, indent=2))
            else:
                print(body.decode('utf-8', errors='replace'))
        except Exception as e:
            print(f"Raw bytes: {body}")
            print(f"(Parse error: {e})")
        
        print(f"\n{'='*80}\n")
        
        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')
    
    def do_GET(self):
        """Handle GET requests"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Test server is running. Send POST requests to see payloads.\n')

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    
    server = HTTPServer(('0.0.0.0', port), RequestHandler)
    
    print(f"{'='*80}")
    print(f"Test HTTP Server - Listening on http://0.0.0.0:{port}")
    print(f"{'='*80}")
    print("\nWaiting for POST requests...")
    print("Press Ctrl+C to stop\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped")
        server.shutdown()

if __name__ == '__main__':
    main()
