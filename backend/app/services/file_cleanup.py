from __future__ import annotations

import time
from pathlib import Path


def delete_file_best_effort(path: Path, *, retries: int = 8, base_delay_seconds: float = 0.25) -> bool:
    """
    Best-effort delete for Windows/Linux.

    Why: on Windows, recently-opened files can be temporarily locked (OSS SDK / AV / file indexer),
    so a single unlink() may fail with PermissionError even though it will succeed shortly after.

    Returns True if the file is deleted (or already missing), False otherwise.
    """
    try:
        p = path.resolve()
    except Exception:
        p = path

    for i in range(max(1, int(retries))):
        try:
            p.unlink(missing_ok=True)  # type: ignore[arg-type]
            return True
        except PermissionError as exc:
            # backoff: 0.25s, 0.5s, 0.75s, ...
            time.sleep(float(base_delay_seconds) * float(i + 1))
            last_exc = exc
        except Exception as exc:
            last_exc = exc
            break

    try:
        print(f"[file_cleanup] Failed to delete local file after retries: {p} ({last_exc})")
    except Exception:
        pass
    return False


