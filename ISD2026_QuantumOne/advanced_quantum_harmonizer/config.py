# config.py

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class MeterProfile:
    name: str
    beats_per_bar: int
    strong_beats: List[int]
    medium_beats: List[int] = field(default_factory=list)
    weak_beats: List[int] = field(default_factory=list)

    def metric_weight(self, beat_in_bar: int) -> float:
        """
        Returns metric importance of a beat within a bar.
        beat_in_bar is zero-based.
        """
        if beat_in_bar in self.strong_beats:
            return 1.40
        if beat_in_bar in self.medium_beats:
            return 1.10
        return 0.85


SUPPORTED_METERS: Dict[str, MeterProfile] = {
    "4/4": MeterProfile(
        name="4/4",
        beats_per_bar=4,
        strong_beats=[0, 2],
        medium_beats=[1],
        weak_beats=[3],
    ),
    "3/4": MeterProfile(
        name="3/4",
        beats_per_bar=3,
        strong_beats=[0],
        medium_beats=[1],
        weak_beats=[2],
    ),
    "2/4": MeterProfile(
        name="2/4",
        beats_per_bar=2,
        strong_beats=[0],
        medium_beats=[],
        weak_beats=[1],
    ),
    "6/8": MeterProfile(
        name="6/8",
        beats_per_bar=6,
        strong_beats=[0, 3],
        medium_beats=[1, 4],
        weak_beats=[2, 5],
    ),
    "3/8": MeterProfile(
        name="3/8",
        beats_per_bar=3,
        strong_beats=[0],
        medium_beats=[1],
        weak_beats=[2],
    ),
        "5/4": MeterProfile(
        name="5/4",
        beats_per_bar=5,
        strong_beats=[0, 3],
        medium_beats=[2],
        weak_beats=[1, 4],
    ),
    "9/8": MeterProfile(
        name="9/8",
        beats_per_bar=9,
        strong_beats=[0, 3, 6],
        medium_beats=[1, 4, 7],
        weak_beats=[2, 5, 8],
    ),
    "12/8": MeterProfile(
        name="12/8",
        beats_per_bar=12,
        strong_beats=[0, 3, 6, 9],
        medium_beats=[1, 4, 7, 10],
        weak_beats=[2, 5, 8, 11],
    ),
    
}


@dataclass
class OptimizerConfig:
    block_size_beats: int = 8
    overlap_beats: int = 2
    transpose_to_c: bool = True
    allow_secondary_dominants: bool = False
    allow_seventh_chords: bool = True
    allow_triads: bool = True
    max_pitch_distance_semitones: int = 24   # 2 octaves
    default_octave_for_export: int = 3

    shots: int = 1024
    qaoa_layers: int = 1
    gamma_steps: int = 16
    beta_steps: int = 12
    phase_scale: float = 1.0

    # scoring weights
    w_melody_fit: float = 1.50
    w_register_fit: float = 0.90
    w_metric_fit: float = 0.70
    w_functional_flow: float = 0.80
    w_common_tone: float = 0.35
    w_overlap_consistency: float = 1.20
    w_strong_beat_penalty: float = 0.80
    w_final_tonic_bonus: float = 1.50
    w_initial_tonic_bonus: float = 1.00

    def validate(self) -> None:
        if self.block_size_beats <= 0:
            raise ValueError("block_size_beats must be > 0")
        if self.overlap_beats < 0:
            raise ValueError("overlap_beats must be >= 0")
        if self.overlap_beats >= self.block_size_beats:
            raise ValueError("overlap_beats must be smaller than block_size_beats")