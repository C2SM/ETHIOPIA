from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isoduration.types import Duration


class TimeUtils:
    @staticmethod
    def duration_is_less_equal_zero(duration: Duration) -> bool:
        if (
            duration.date.years == 0
            and duration.date.months == 0
            and duration.date.days == 0
            and duration.time.hours == 0
            and duration.time.minutes == 0
            and duration.time.seconds == 0
            or (
                duration.date.years < 0
                or duration.date.months < 0
                or duration.date.days < 0
                or duration.time.hours < 0
                or duration.time.minutes < 0
                or duration.time.seconds < 0
            )
        ):
            return True
        return False


class ParseUtils:
    @staticmethod
    def entries_to_dicts(entries: list[str | dict[str, dict]]) -> dict[str, dict | None]:
        """
        We have often expressions that can be dicts or str during the parsing that are always converted to dicts to simplify handling

        .. yaml
            - key_1
            - key_2:
                property: true

        When parsing this results in an object of the form [key_1, {key_2: {property: true}}]. This function converts this to {key_1: None, key_2: {property: true}}
        """
        output_dict: dict[str, dict | None] = {}
        for entry in entries:
            if isinstance(entry, dict):
                output_dict.update(entry)
            else:
                output_dict[entry] = None
        return output_dict
