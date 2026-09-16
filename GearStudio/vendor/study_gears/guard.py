"""Bounded cooperative execution for the privately vendored geometry engine.

No Fusion imports: the builder supplies event-pump and document-check callbacks.
An individual native Fusion kernel call cannot be interrupted by Python.
"""
from contextlib import contextmanager
from time import monotonic


class GeometryCancelled(RuntimeError):
    pass


class GeometryBudgetExceeded(RuntimeError):
    pass


_active = None


class Budget:
    def __init__(self, cancelled=None, pump=None, seconds=150.0, iterations=2000000):
        self.cancelled = cancelled or (lambda: False)
        self.pump = pump
        self.deadline = monotonic() + seconds
        self.remaining = iterations
        self.next_poll = 0.0
        self.polling = False

    def check(self, force=False):
        self.remaining -= 1
        if self.remaining < 0:
            raise GeometryBudgetExceeded(
                "The geometric calculation exceeded its iteration budget. "
                "Reduce the tooth count, face width or helix angle."
            )
        now = monotonic()
        if now > self.deadline:
            raise GeometryBudgetExceeded(
                "The build exceeded its time budget. The existing gear was preserved. "
                "Try a narrower face or fewer teeth."
            )
        if self.polling or (not force and now < self.next_poll):
            return
        self.next_poll = now + 0.08
        if self.cancelled():
            raise GeometryCancelled("Build cancelled. The existing gear was preserved.")
        if self.pump:
            self.polling = True
            try:
                self.pump()
            finally:
                self.polling = False
        if self.cancelled():
            raise GeometryCancelled("Build cancelled. The existing gear was preserved.")


def checkpoint(force=False):
    if _active is not None:
        _active.check(force)


@contextmanager
def bounded(cancelled=None, pump=None, seconds=150.0, iterations=2000000):
    global _active
    if _active is not None:
        raise RuntimeError("A gear calculation is already running.")
    budget = Budget(cancelled, pump, seconds, iterations)
    _active = budget
    try:
        checkpoint(force=True)
        yield budget
    finally:
        _active = None
