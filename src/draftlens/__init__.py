"""DraftLens — data-driven NBA Draft decision support.

Reusable analytical logic lives in this package; `scripts/` holds thin command
line entry points that call into it. See docs/ARCHITECTURE.md.

The two model stages are FROZEN (DEC-080..091). Changing their configuration
requires an explicit decision recorded in docs/DECISIONS.md, not a code edit.
"""

__version__ = "0.6.0"
