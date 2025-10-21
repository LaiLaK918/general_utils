import asyncio

from general_utils.utils.timing import measure_time


def my_callback(func, args, kwargs, elapsed):  # noqa: D103
    print(f"[CALLBACK] {func.__name__} = {elapsed:.3f}s")


def my_metric_collector(name, elapsed):  # noqa: D103
    print(f"[METRIC] {name} -> {elapsed:.3f}s")


@measure_time(
    threshold_warning=0.5,
    on_complete_callback=my_callback,
    metric_collector=my_metric_collector,
    tag="sync",
    is_return_measured_time=True,
)
def slow_task(x):  # noqa: D103
    import time

    time.sleep(x)
    return x * 2


@measure_time(
    is_async=True,
    threshold_warning=0.5,
    tag="async",
    metric_collector=my_metric_collector,
    is_return_measured_time=True,
)
async def slow_async(x):  # noqa: D103
    await asyncio.sleep(x)
    return x * 3


async def main():  # noqa: D103
    print(slow_task(0.7))
    print(await slow_async(1.0))


if __name__ == "__main__":
    asyncio.run(main())
