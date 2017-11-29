import pytest
import time

from .._core.tests.tutil import slow
from .. import _core
from ..testing import assert_checkpoints
from .._timeouts import *


async def check_takes_about(f, expected_dur):
    start = time.monotonic()
    result = await _core.Result.acapture(f)
    dur = time.monotonic() - start
    print(dur / expected_dur)
    # 1.2 is an arbitrary fudge factor because there's always some delay
    # between when we become eligible to wake up and when we actually do. We
    # used to sleep for 0.05, and regularly observed overruns of 1.6x on
    # Appveyor, and then started seeing overruns of 2.3x on Travis's MacOS, so
    # now we bumped up the sleep to 1 second, marked the tests as slow, and
    # hopefully now the proportional error will be less huge.
    assert 1 <= (dur / expected_dur) < 1.2
    return result.unwrap()


# How long to (attempt to) sleep for when testing. Smaller numbers make the
# test suite go faster.
TARGET = 1.0


@slow
async def test_sleep():
    async def sleep_1():
        await sleep_until(_core.current_time() + TARGET)

    await check_takes_about(sleep_1, TARGET)

    async def sleep_2():
        await sleep(TARGET)

    await check_takes_about(sleep_2, TARGET)

    with pytest.raises(ValueError):
        await sleep(-1)

    with assert_checkpoints():
        await sleep(0)
    # This also serves as a test of the trivial move_on_at
    with move_on_at(_core.current_time()):
        with pytest.raises(_core.Cancelled):
            await sleep(0)


@slow
async def test_move_on_after():
    with pytest.raises(ValueError):
        with move_on_after(-1):
            pass  # pragma: no cover

    async def sleep_3():
        with move_on_after(TARGET):
            await sleep(100)

    await check_takes_about(sleep_3, TARGET)


@slow
async def test_fail():
    async def sleep_4():
        with fail_at(_core.current_time() + TARGET):
            await sleep(100)

    with pytest.raises(TooSlowError):
        await check_takes_about(sleep_4, TARGET)

    with fail_at(_core.current_time() + 100):
        await sleep(0)

    async def sleep_5():
        with fail_after(TARGET):
            await sleep(100)

    with pytest.raises(TooSlowError):
        await check_takes_about(sleep_5, TARGET)

    with fail_after(100):
        await sleep(0)

    with pytest.raises(ValueError):
        with fail_after(-1):
            pass  # pragma: no cover
