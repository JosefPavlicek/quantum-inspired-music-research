"""Decision-log export.

Target outputs:
- selected chord symbol
- Roman numeral
- measure / beat / duration
- every score component
- local score
- accumulated path score
- top alternative candidates
- JSON and CSV
"""


def export_json(decisions, path):
    raise NotImplementedError


def export_csv(decisions, path):
    raise NotImplementedError
