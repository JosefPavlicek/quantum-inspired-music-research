# beat_representation.py

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BeatEvent:
    global_beat_index: int
    bar_index: int
    beat_in_bar: int
    notes_midi: List[int] = field(default_factory=list)   # [] = rest
    duration_units: float = 1.0
    is_strong: bool = False
    metric_weight: float = 1.0
    meter: str = "4/4"

    @property
    def is_rest(self) -> bool:
        return len(self.notes_midi) == 0

    @property
    def lowest_note(self) -> Optional[int]:
        if not self.notes_midi:
            return None
        return min(self.notes_midi)

    @property
    def highest_note(self) -> Optional[int]:
        if not self.notes_midi:
            return None
        return max(self.notes_midi)

    @property
    def note_count(self) -> int:
        return len(self.notes_midi)


@dataclass
class BeatSequence:
    events: List[BeatEvent]

    def __len__(self) -> int:
        return len(self.events)

    def __getitem__(self, item):
        return self.events[item]

    def slice(self, start: int, end: int) -> "BeatSequence":
        return BeatSequence(events=self.events[start:end])

    def global_indices(self) -> List[int]:
        return [e.global_beat_index for e in self.events]