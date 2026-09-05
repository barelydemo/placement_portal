"""A single clock for deadline arithmetic.

Deadlines and interview slots come from the browser as *local calendar* values
("2026-09-30", "2026-12-01T10:30") and are stored naive, exactly as entered — a
date-only deadline means the end of that day where the institute is.

So anything compared against them must use the same frame: server-local naive
time, not UTC. Mixing the two silently shifts every deadline by the machine's
UTC offset (5.5 hours in IST), which is enough to keep an expired drive visible
or push a closing drive outside the reminder window.

Audit timestamps (`created_at`, `applied_at`) remain UTC and are only ever
compared against other UTC values, so they are unaffected.
"""

from datetime import datetime


def now() -> datetime:
    """Current server-local time, naive — the frame deadlines are stored in."""
    return datetime.now()
