from datetime import datetime

import pytest

from tools.timedate import get_current_time


def test_get_current_time_default_utc():
    result = get_current_time()
    parsed = datetime.fromisoformat(result)
    assert parsed.utcoffset().total_seconds() == 0


def test_get_current_time_with_timezone():
    result = get_current_time("Asia/Ho_Chi_Minh")
    parsed = datetime.fromisoformat(result)
    assert parsed.utcoffset().total_seconds() == 7 * 3600


def test_get_current_time_unknown_timezone_raises():
    with pytest.raises(ValueError, match="Unknown timezone"):
        get_current_time("Not/AZone")
