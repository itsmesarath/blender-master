#!/usr/bin/env python3
"""Print the project-type recognition for a one-line request.
Usage: python recognize.py "a game-ready sci-fi crate for Unity"
"""
import json
import sys

from bm_plan import recognise

if __name__ == "__main__":
    print(json.dumps(recognise(" ".join(sys.argv[1:])), indent=2))
