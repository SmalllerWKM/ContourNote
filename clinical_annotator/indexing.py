"""Background JSON metadata indexing; never touches GUI objects."""
import json
import threading
from PySide6.QtCore import QObject, QRunnable, Signal


class IndexSignals(QObject):
    batch = Signal(int, object, int)


class AnnotationIndex(QRunnable):
    def __init__(self, generation, targets, annotated):
        super().__init__()
        self.signals = IndexSignals()
        self.generation, self.targets, self.annotated = generation, targets, annotated
        self.cancelled = threading.Event()

    def run(self):
        batch = []
        for index, path in enumerate(self.targets):
            if self.cancelled.is_set():
                return
            try:
                data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
                shapes = data.get('shapes', [])
                names = {s['label'] for s in shapes if isinstance(s, dict) and isinstance(s.get('label'), str)}
                result = (index, self.annotated(data), len(shapes), sorted(names), False)
            except (OSError, ValueError, TypeError, AttributeError):
                result = (index, False, 0, [], True)
            batch.append(result)
            if len(batch) == 100 or index == len(self.targets)-1:
                self.signals.batch.emit(self.generation, batch, index+1)
                batch = []
