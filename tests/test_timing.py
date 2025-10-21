import asyncio
import time

from general_utils.utils.log_common import build_logger
from general_utils.utils.timing import measure_time


# ----- Sync example -----
@measure_time
def slow_sync():  # noqa: D103
    time.sleep(1.2)
    return "sync done"


# ----- Async example -----
@measure_time(is_async=True)
async def slow_async():  # noqa: D103
    await asyncio.sleep(1.0)
    return "async done"


# ----- Custom logger example -----
custom_logger = build_logger("timing_custom")


@measure_time(logger=custom_logger, level="debug")
def quick_sync():  # noqa: D103
    time.sleep(0.2)
    return "quick done"


async def main():  # noqa: D103
    print("→ Running sync test")
    print(slow_sync())

    print("→ Running async test")
    print(await slow_async())

    print("→ Running custom logger test")
    print(quick_sync())


if __name__ == "__main__":
    asyncio.run(main())
