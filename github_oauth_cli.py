#!/usr/bin/env python3
"""
DEPRECATED — use oauth_cli.py instead.
This wrapper preserves backward compatibility for existing users.
"""

import sys
from oauth_cli import main

if __name__ == "__main__":
    sys.exit(main())
