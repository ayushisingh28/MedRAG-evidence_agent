import threading
from collections import Counter


class Metrics:
    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()
        self._lock = threading.Lock()

    def increment(self, metric: str) -> None:
        with self._lock:
            self._counts[metric] += 1

    def prometheus(self) -> str:
        with self._lock:
            lines = ["# TYPE medrag_requests_total counter"]
            lines.extend(
                f'medrag_requests_total{{kind="{key}"}} {value}'
                for key, value in self._counts.items()
            )
        return "\n".join(lines) + "\n"


metrics = Metrics()
