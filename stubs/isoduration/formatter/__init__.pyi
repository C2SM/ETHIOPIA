from isoduration.constants import PERIOD_PREFIX as PERIOD_PREFIX
from isoduration.formatter.checking import check_global_sign as check_global_sign
from isoduration.formatter.formatting import format_date as format_date, format_time as format_time
from isoduration.types import Duration as Duration

def format_duration(duration: Duration) -> str: ...
