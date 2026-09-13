#!/usr/bin/env python3
"""
Clairvoy Command Line Interface
"""

import argparse
import sys
import os
from clairvoy import __version__
from clairvoy.engines.storage_engine import StorageEngine

def print_banner():
    banner = r"""
   _____ _       _                              
  / ____| |     (_)                             
 | |    | | __ _ _ _ ____   _____  _   _        
 | |    | |/ _` | | '__\ \ / / _ \| | | |       
 | |____| | (_| | | |   \ V / (_) | |_| |       
  \_____|_|\__,_|_|_|    \_/ \___/ \__, |       
                                    __/ |       
  Local-First AI Deduplication Engine|___/  v""" + __version__ + "\n"
    print(banner)

def main():
    parser = argparse.ArgumentParser(
        prog="clairvoy",
        description="Clairvoy: Local-first AI storage deduplication engine"
    )
    parser.add_argument("--version", "-v", action="version", version=f"clairvoy {__version__}")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan a directory for duplicate files")
    scan_parser.add_argument("path", help="Directory path to scan")
    scan_parser.add_argument("--output", "-o", default=None, help="Directory to save report files")
    scan_parser.add_argument("--quarantine", action="store_true", help="Automatically generate safe quarantine script")
    
    # UI command
    ui_parser = subparsers.add_parser("ui", help="Launch the interactive Web App")
    ui_parser.add_argument("--port", "-p", type=int, default=8000, help="Web server port (default: 8000)")
    ui_parser.add_argument("--host", default="127.0.0.1", help="Web server host (default: 127.0.0.1)")

    args = parser.parse_args()

    if not args.command:
        print_banner()
        parser.print_help()
        sys.exit(0)

    if args.command == "scan":
        print_banner()
        target_dir = os.path.abspath(args.path)
        if not os.path.isdir(target_dir):
            print(f"Error: Directory '{target_dir}' does not exist.")
            sys.exit(1)
            
        engine = StorageEngine(target_dir, args.output)
        engine.run()

    elif args.command == "ui":
        print_banner()
        print(f"Starting Clairvoy Web UI at http://{args.host}:{args.port} ...")
        try:
            import uvicorn
            from clairvoy.web.app import app
            uvicorn.run(app, host=args.host, port=args.port)
        except ImportError:
            print("Web dependencies not found. Install them with: pip install 'clairvoy[ml]' or pip install fastapi uvicorn")
            sys.exit(1)

if __name__ == "__main__":
    main()
