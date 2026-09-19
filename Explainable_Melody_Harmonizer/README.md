# Explainable Melody Harmonizer (EMH)

Transparent, reproducible melody harmonization from monophonic MusicXML.

## Research context
Designed as an explainable baseline for the research line:

> Computational representation of human harmonic decision-making: from formal models and explainable generation to education and human musical intention.

EMH is a separate approach alongside the existing quantum-inspired harmonizer. It is not its replacement.

## Core principles
- Input: monophonic MusicXML only.
- No access to reference/original chords during generation.
- Meter-aware and duration-aware harmonic segmentation.
- Explicit chord candidates and scoring components.
- Global Viterbi-like / dynamic-programming optimization.
- Full decision log with alternatives.
- Reproducible configuration.

## Planned supported meters
- 2/4
- 3/4
- 4/4
- 6/8
- 12/8

Compound meters remain compound meters; e.g. 12/8 is not converted to 6/4.

## Project structure
- `harmonizer.py` – command-line entry point
- `config.yaml` – model parameters
- `emh/model.py` – internal data structures
- `emh/musicxml_loader.py` – MusicXML parsing
- `emh/meter.py` – meter and metric-strength logic
- `emh/segmentation.py` – harmonic decision grid
- `emh/harmony.py` – chord candidate generation
- `emh/scoring.py` – explicit scoring components
- `emh/optimizer.py` – global DP/Viterbi optimization
- `emh/explanation.py` – JSON/CSV decision log
- `emh/musicxml_writer.py` – generated `<harmony>` output
- `tests/` – unit tests and MusicXML fixtures
- `examples/` – example inputs
- `results/` – generated outputs

## Experimental firewall
The harmonizer accepts melody and configuration only. Reference/original harmony must not be supplied to the generator. Any later comparison with human/original harmony belongs in a separate evaluation stage.

## Status
Initial project skeleton. Algorithm implementation will be added incrementally after validation of each component.
