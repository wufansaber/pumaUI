from __future__ import annotations

from math import ceil
from time import monotonic
from typing import Callable, Optional

from ...qt_compat import QTimer


class TimedWaferOperation:
    """Non-blocking wafer transfer timer with deterministic failure simulation."""

    MODES = ("Normal", "Timeout", "Transfer Exception")

    def __init__(
        self,
        owner,
        *,
        duration_ms: int = 10000,
        timeout_ms: int = 12000,
        tick_ms: int = 100,
        on_progress: Optional[Callable[[dict], None]] = None,
        on_active_changed: Optional[Callable[[bool], None]] = None,
    ):
        self.duration_ms = max(0, int(duration_ms))
        self.timeout_ms = max(self.duration_ms, int(timeout_ms))
        self.tick_ms = max(10, int(tick_ms))
        self.on_progress = on_progress
        self.on_active_changed = on_active_changed
        self.timer = QTimer(owner)
        self.timer.setInterval(self.tick_ms)
        self.timer.timeout.connect(self._tick)
        self.active = False
        self.operation = ""
        self.failure_mode = "Normal"
        self.elapsed_ms = 0
        self.last_outcome = "Idle"
        self.last_error = ""
        self._on_success = None
        self._on_failure = None
        self._started_at = 0.0

    def start(
        self,
        operation: str,
        *,
        failure_mode: str = "Normal",
        on_success: Optional[Callable[[], None]] = None,
        on_failure: Optional[Callable[[str, str], None]] = None,
    ) -> bool:
        if self.active:
            return False
        self.operation = operation
        self.failure_mode = failure_mode if failure_mode in self.MODES else "Normal"
        self.elapsed_ms = 0
        self._started_at = monotonic()
        self.last_outcome = "Running"
        self.last_error = ""
        self._on_success = on_success
        self._on_failure = on_failure
        self.active = True
        self._notify_active()
        self._notify_progress()
        if self.duration_ms == 0:
            if self.failure_mode == "Normal":
                self._complete()
            elif self.failure_mode == "Transfer Exception":
                self._fail("Transfer Exception", "WH-TRANSFER-001")
            else:
                self._fail("Timed Out", "WH-TIMEOUT-001")
        else:
            self.timer.start()
        return True

    def abort(self) -> bool:
        if not self.active:
            return False
        self._fail("Aborted", "WH-ABORT-001")
        return True

    def advance_for_test(self, milliseconds: int):
        """Advance deterministically without sleeping; used by UI workflow tests."""
        self.timer.stop()
        target = self.elapsed_ms + max(0, int(milliseconds))
        while self.active and self.elapsed_ms < target:
            self.elapsed_ms += min(self.tick_ms, target - self.elapsed_ms)
            self._evaluate()

    def snapshot(self) -> dict:
        limit = self.timeout_ms if self.failure_mode == "Timeout" else self.duration_ms
        remaining_ms = max(0, limit - self.elapsed_ms)
        progress = 100 if limit == 0 else min(100, int(self.elapsed_ms * 100 / limit))
        return {
            "active": self.active,
            "operation": self.operation,
            "phase": self._phase(),
            "elapsed_ms": self.elapsed_ms,
            "remaining_seconds": int(ceil(remaining_ms / 1000.0)),
            "progress": progress,
            "failure_mode": self.failure_mode,
            "outcome": self.last_outcome,
            "error": self.last_error,
        }

    def _tick(self):
        self.elapsed_ms = int((monotonic() - self._started_at) * 1000)
        self._evaluate()

    def _evaluate(self):
        if not self.active:
            return
        if (
            self.failure_mode == "Transfer Exception"
            and self.elapsed_ms >= max(self.tick_ms, int(self.duration_ms * 0.4))
        ):
            self._fail("Transfer Exception", "WH-TRANSFER-001")
            return
        if self.failure_mode == "Timeout" and self.elapsed_ms >= self.timeout_ms:
            self._fail("Timed Out", "WH-TIMEOUT-001")
            return
        if self.failure_mode == "Normal" and self.elapsed_ms >= self.duration_ms:
            self._complete()
            return
        self._notify_progress()

    def _phase(self) -> str:
        if self.operation == "load_align":
            ratio = self.elapsed_ms / max(1, self.duration_ms)
            if ratio < 0.6:
                return "Loading a Wafer"
            if ratio < 0.82:
                return "Locating Wafer Center"
            return "Aligning Wafer"
        if self.operation == "load":
            ratio = self.elapsed_ms / max(1, self.duration_ms)
            return "Loading a Wafer" if ratio < 0.75 else "Locating Wafer Center"
        if self.operation == "unload":
            return "Unloading a Wafer"
        return "Wafer Operation"

    def _complete(self):
        callback = self._on_success
        self.timer.stop()
        self.active = False
        self.elapsed_ms = self.duration_ms
        self.last_outcome = "Completed"
        self.last_error = ""
        self._notify_progress()
        self._notify_active()
        if callback:
            callback()

    def _fail(self, outcome: str, error_code: str):
        callback = self._on_failure
        self.timer.stop()
        self.active = False
        self.last_outcome = outcome
        self.last_error = error_code
        self._notify_progress()
        self._notify_active()
        if callback:
            callback(outcome, error_code)

    def _notify_progress(self):
        if self.on_progress:
            self.on_progress(self.snapshot())

    def _notify_active(self):
        if self.on_active_changed:
            self.on_active_changed(self.active)
