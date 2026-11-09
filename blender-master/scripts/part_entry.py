"""Entry point launched inside Blender for one part. See lib/bm_part.py."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import bm_part  # noqa: E402

result = bm_part.run_part()
print(f"[blender-master] part {result['part']} -> {result['status']}")
sys.exit(0)
