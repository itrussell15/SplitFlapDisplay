# Trigger foundation

The existing `Updater` combines a timer with an inherited `update()` method.
`Trigger` separates deciding **when** to run from deciding **what** to do. A
playlist or display item can own a trigger and supply its own method as the
callback. Only triggering strategies inherit from `Trigger`.

This first step adds `software/app/components/core/trigger.py` independently.
Existing `Updater` consumers still use their current implementation. An
`IntervalTrigger` supplies timer-based scheduling. Polling strategies,
playlist integration, and item integration come later.

## Contract

`Trigger` is an abstract class with three required members and one shared method:

| Member | Meaning |
| --- | --- |
| `start()` | Enable triggering. Repeated calls are harmless. |
| `stop()` | Disable triggering. Repeated calls are harmless. A running callback may finish. |
| `is_active` | Whether triggering is enabled, including while waiting between events. |
| `invoke()` | Call the supplied callback once if active. Return `True` if called, `False` if inactive or the strategy skips an overlapping call. |

A new trigger is inactive and can be restarted after stopping. `start()` does
not run the callback. This keeps enabling a schedule separate from performing
an initial update; a future owner can explicitly do that update when needed.

The constructor requires one synchronous, zero-argument callback. Bound methods
work directly; use a closure or `functools.partial` when arguments are needed.
Callback results are ignored. Exceptions propagate from `invoke()`, and do not
automatically deactivate the trigger. A future background strategy must define
how it reports failures and whether it keeps scheduling after them.

## Try it without scheduling

`ManualTrigger` provides the smallest concrete implementation. Run this from
the `software/` directory:

```python
from app.components.core.trigger import ManualTrigger

trigger = ManualTrigger(lambda: print("Time to update"))

trigger.invoke()  # False: initially inactive
trigger.start()   # Enables the trigger; no output yet
trigger.invoke()  # Prints "Time to update" and returns True
trigger.invoke()  # Prints again; one callback per invocation
trigger.stop()
trigger.invoke()  # False: stopped
```

Manual triggers are used on one thread and create no background work.

## Repeated interval callbacks

`IntervalTrigger` uses the chained `threading.Timer` approach from
`TimeBasedUpdater` and accepts the existing `UpdateFrequency` object. Each
timer uses `frequency.interval`, combining its minutes and seconds:

```python
import time
from app.components.core.trigger import IntervalTrigger
from app.components.core.updater import UpdateFrequency

frequency = UpdateFrequency(seconds=5)
trigger = IntervalTrigger(lambda: print("Time to update"), frequency=frequency)
trigger.start()  # Returns immediately; first callback runs after five seconds
try:
    time.sleep(16)  # Keep this example alive to see about three callbacks
finally:
    trigger.stop()
```

After each callback finishes, the trigger schedules the next timer. A callback
that takes two seconds with a five-second interval therefore starts about
seven seconds after the previous callback started. This matches the previous
updater's delay between completed work and its next invocation. Unlike the
old updater's default, `start()` waits for the first interval, as specified by
the new trigger contract. Perform an initial update explicitly if needed.

Repeated `start()` calls do not add timers. `stop()` cancels pending work and
returns without waiting for an invocation already in progress. Cancelled
timers carry a run identifier so a late delivery cannot invoke a callback or
reschedule work after stopping or restarting.

Callbacks never overlap. If an explicit `invoke()` occurs during another
callback, it returns `False`. If a timer expires during an explicit callback,
that timer's invocation is skipped and the next interval begins when the
running callback finishes. Otherwise an explicit invocation leaves the
pending timer's schedule intact. Restarting during a callback defers the new
run's first timer until that callback finishes.

Callback failures in timer threads are logged, and another timer is scheduled.
Failures from an explicit `invoke()` propagate to its caller. Callbacks can
call `stop()` themselves. Timer threads are daemons; they do not keep an
otherwise finished application alive. `trigger.frequency` exposes the original
object. Changing its `minutes` or `seconds` affects the next timer scheduled;
a timer already waiting keeps its existing interval.

## Composition in a future owner

This is a standalone example of the intended relationship, rather than a
change to the current playlist or item classes:

```python
class ExampleItem:
    def __init__(self):
        self.trigger = ManualTrigger(self.update)

    def update(self):
        print("Generate and display the next output")

    def start(self):
        self.update()         # Owner chooses to display an initial value
        self.trigger.start()

    def stop(self):
        self.trigger.stop()
```

Later, an owner could accept a trigger factory, constructing a strategy with
`self.update` as its callback. That lets callers choose the strategy without
requiring the owner to inherit scheduling behavior or replacing callbacks on
an already-running trigger.

`IntervalTrigger` schedules a callback after each interval. A future
`PollingTrigger` would check a condition and call `invoke()` when its policy
says the condition warrants an update. Interval configuration and next-run
timing belong to the interval strategy; polling conditions belong to the
polling strategy. Neither is required by the abstract class. Strategies that
introduce background work must coordinate start, stop, and callback execution
and decide how to handle overlapping events.

Verify the triggers without hardware. The interval tests use controlled timer
delivery for lifecycle races and real timer threads for repeated callbacks:

```bash
cd software
../.venv/bin/python -m unittest app.components.test.test_trigger app.components.test.test_interval_trigger -v
```
