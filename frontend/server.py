#!/usr/bin/env python3
"""
Simple HTTP server for serving the Price Comparison Tool frontend
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

# Configuration
PORT = 3010
FRONTEND_DIR = Path(__file__).parent


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler with CORS support"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)
    
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle preflight requests"""
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        """Custom logging format"""
        print(f"[{self.log_date_time_string()}] {format % args}")


def main():
    """Start the HTTP server"""
    try:
        # Change to frontend directory
        os.chdir(FRONTEND_DIR)
        
        # Create server
        with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
            print(f"Frontend server starting on port {PORT}")
            print(f"Serving files from: {FRONTEND_DIR}")
            print(f"Access the application at: http://localhost:{PORT}")
            print(f"Press Ctrl+C to stop the server")
            print("-" * 50)
            
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n\nServer stopped by user")
                sys.exit(0)
                
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"Error: Port {PORT} is already in use!")
            print(f"   Try stopping any other servers running on port {PORT}")
            print(f"   or change the PORT variable in this script")
        else:
            print(f"Error starting server: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()