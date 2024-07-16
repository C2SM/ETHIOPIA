from isoduration.parser.exceptions import EmptyDuration as EmptyDuration
from isoduration.parser.parsing import parse_date_duration as parse_date_duration
from isoduration.parser.util import is_period as is_period
from isoduration.types import Duration as Duration

def parse_duration(duration_str: str) -> Duration: ...
