from datetime import datetime
from isoduration.operations.util import max_day_in_month as max_day_in_month, mod2 as mod2, mod3 as mod3, quot2 as quot2, quot3 as quot3
from isoduration.types import Duration as Duration

def add(start: datetime, duration: Duration) -> datetime: ...
