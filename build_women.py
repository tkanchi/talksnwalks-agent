"""Women content entry point.

This intentionally keeps the existing, proven TalksNWalks pipeline unchanged.
The current data/quotes.csv and illustrations/ directory are treated as the
women library until those binary illustration files are migrated into
illustrations/women/.
"""

import build_reel


if __name__ == "__main__":
    build_reel.main()
