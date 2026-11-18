# Trigger foundation

The existing `Updater` combines a timer with an inherited `update()` method.
`Trigger` separates deciding **when** to run from deciding **what** to do. A
playlist or display item can own a trigger and supply its own method as the
callback. Only triggering strategies inherit from `Trigger`.

`PlaylistItem` and `DisplayItem` own triggers created by factories. The example
clock, weather, and static items use that interface. The core playlist owns a
one-shot advancement trigger and stores a duration per entry. `DisplayPlaylist`
supplies shared display configuration and inherits playback from `Playlist`.
The API request and status fields still need migration.

## Contract

`Trigger` is an abstract class with three required members and one shared method:

| Member | Meaning |
| --- | --- |
| `start()` | Enable triggering. Repeated calls are harmless. |
| `stop()` | Disable triggering. Repeated calls are harmless. A running callback may finish. |
| `is_active` | Whether triggering is enabled, including while waiting between events. |
| `invoke()` | Call the supplied callback once if active. Return `True` if called, `False` if inactive or the strategy skips an overlapping call. |

A new trigger is inactive and can be restarted after stopping. `start()` does
not run the callback. Items perform their initial update in `activate()`.

The constructor requires one synchronous, zero-argument callback. Bound methods
work directly; use a closure or `functools.partial` when arguments are needed.
Callback results are ignored. Exceptions propagate from `invoke()`. Interval
and polling triggers log background callback failures and keep scheduling;
one-shot triggers finish their run even if the callback fails.

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

## Polling with a cooldown

`PollingTrigger` checks a zero-argument evaluation function on an
`UpdateFrequency` schedule. A true result invokes its callback unless a
cooldown is active. Polling continues during cooldown and suppressed results
do not extend it:

```python
from app.components.core.trigger import PollingTrigger
from app.components.core.updater import UpdateFrequency

trigger = PollingTrigger(
    callback=lambda: print("Update accepted"),
    frequency=UpdateFrequency(seconds=0.1),
    evaluation=lambda: True,
    cooldown=UpdateFrequency(seconds=5),
)
```

Each accepted result starts a cooldown before the callback runs, including if
the callback fails. `cooldown_status` exposes a `TimeStatus` with elapsed and
remaining time. It is `None` before the first accepted result. Both cooldowns
and countdown status use `TimeStatus`'s existing wall-clock timestamps.

## One-shot countdowns

`OneShotTrigger` invokes its callback once after its duration, then becomes
inactive. It supports cancellation, early invocation, and restarting:

```python
from app.components.core.trigger import OneShotTrigger
from app.components.core.updater import UpdateFrequency

trigger = OneShotTrigger(
    callback=lambda: print("Countdown finished"),
    duration=UpdateFrequency(seconds=10),
)
trigger.start()
# trigger.time_status exposes the countdown's elapsed and remaining time.
# Keep the application alive for the timer to fire, or cancel with stop().
```

An explicit `invoke()` fires early and cancels the pending timer. Repeated
`start()` calls while active do not reset the countdown. The trigger becomes
inactive before its callback runs. This strategy can later drive playlist
advancement independently of an item's content refresh trigger.

## Items and trigger factories

An item passes its `_execute_update()` callback to the supplied factory. The
factory creates a new trigger bound to that item. Items use `activate()` and
`deactivate()`; triggers use `start()` and `stop()`:

```python
from app.components.core.playlist import PlaylistItem
from app.components.core.trigger import ManualTrigger

class ExampleItem(PlaylistItem):
    def update(self):
        print("Update this item's content")

item = ExampleItem("Example", trigger_factory=ManualTrigger)
item.activate()        # Performs the initial update, then starts the trigger
item.trigger.invoke()  # Performs another update
item.deactivate()      # Stops the item's trigger
```

Pass `update_on_start=False` to `activate()` to defer the initial update. An
item stays active until deactivated, including if it has no trigger or its
one-shot trigger completes. `DisplayItem._execute_update()` supplies display
information to `update(display_info)`, resolves generated flap values, and
renders the result.

## Playlist entries and variable durations

`PlaylistEntry` pairs an item with an `UpdateFrequency` duration and a unique
entry UUID. The item keeps its own content refresh trigger. Construct a playlist
from entries, or add an item and duration directly:

```python
from app.components.core.playlist import Playlist, PlaylistItem, PlaylistEntry
from app.components.core.updater import UpdateFrequency

class ExampleItem(PlaylistItem):
    def update(self):
        print(f"Showing {self.name}")

playlist = Playlist([
    PlaylistEntry(ExampleItem("A"), UpdateFrequency(minutes=1)),
    PlaylistEntry(ExampleItem("B"), UpdateFrequency(seconds=10)),
])
# Alternatively: playlist.add_entry(item, UpdateFrequency(seconds=30))
playlist.start()  # Shows A, then begins its 60-second countdown
playlist.next()   # Shows B immediately and begins a new 10-second countdown
playlist.stop()
```

Each countdown begins after the initial content update completes. When it
expires, the playlist deactivates the outgoing item, activates the next one,
and starts a fresh `OneShotTrigger` for that entry. Entries wrap around.
`time_status` comes from that trigger and is `None` while stopped, during
activation, or when there is only one entry. A single entry remains active
without repeated advancement; its content trigger can keep refreshing it.

`entries` and `current_entry` expose durations; `items` and `current_item` expose
content objects. `get_entry()` and `remove_entry()` use zero-based indices.
Stop the playlist before adding or removing entries. Adding an entry only edits
the queue; timers start when playback starts. Removing an earlier entry preserves
the selected entry. Changing a duration's minutes or seconds applies on the next
activation, leaving a pending timer intact.

Repeated `start()` and `stop()` calls are harmless. Stopped `next()` changes only
the selection; `update()` advances only while active. Controls use one lock, so
each lifecycle operation finishes before another thread proceeds. `stop()` waits
for an activation already running, then cancels the timer and deactivates the
item. Activation failures stop playback and propagate to explicit callers;
background failures are logged by the one-shot trigger.

The playback methods directly show the sequence:

- `start()`: activate the current item, then schedule its timer.
- `next()`: stop the old timer, deactivate the old item, select and activate the
  next item, then schedule its timer.
- `stop()`: stop the timer and deactivate the current item.

`_schedule_timer()` creates a `OneShotTrigger` using the current entry's duration.
Its callback checks that it is still the playlist's current timer before calling
`next()`. `_stop_timer()` cancels that trigger and clears the reference. This
ignores callbacks from replaced timers without a playlist generation counter.
There is no transition loop or deferred restart handling.

## Display playlists

`DisplayPlaylist` uses the same entries, durations, and playback methods as
`Playlist`. It restricts entries to `DisplayItem` instances and supplies their
shared display information, resolver, and output function. Entries can be added
before or after setup: setters configure existing items, and later additions
receive the stored configuration. Stop playback before changing that setup.

This example runs without hardware:

```python
from app.components.core.playlist import PlaylistEntry
from app.components.core.updater import UpdateFrequency
from app.components.display.base_apps.static import StaticDisplayItem
from app.components.display.playlist import DisplayPlaylist
from control.source.display_controller import DisplayInfo

outputs = []
playlist = DisplayPlaylist(
    entries=[
        PlaylistEntry(
            StaticDisplayItem("A", {(1, 1): 3}, needs_resolving=False),
            UpdateFrequency(minutes=1),
        ),
        PlaylistEntry(
            StaticDisplayItem("B", {(1, 1): 4}, needs_resolving=False),
            UpdateFrequency(seconds=10),
        ),
    ],
    app_folders=[],
)
playlist.add_display_info(DisplayInfo(rows=3, columns=15, modules=[]))
playlist.add_resolve_function(lambda flaps: flaps)
playlist.add_display_function(outputs.append)
playlist.start()  # Renders A and starts its 60-second timer
playlist.next()   # Renders B and starts its 10-second timer
playlist.stop()
print(outputs)  # [{(1, 1): 3}, {(1, 1): 4}]
```

Use `playlist.add_entry(item, duration)` or `playlist.add_entry(entry)` for later
additions while stopped. `apps` and `available_apps` expose the app loader; the
default source is `display/base_apps`. Pass `app_folders=[]` to disable discovery
or pass a list of custom source directories.

## Example display apps

The example apps accept an optional `trigger_factory`:

| App | Default behavior |
| --- | --- |
| `DateTimeApp` | Initial update, then an interval trigger every 10 seconds |
| `TemperatureApp` | Initial update, then an interval trigger every 60 seconds |
| `StaticDisplayItem` | One initial update and no recurring trigger |

Each default factory constructs a fresh trigger and `UpdateFrequency` object.
Passing `None` disables recurring updates; passing another factory selects a
different strategy. Factories are excluded from serialized item parameters and
the app loader's user-facing parameter metadata.

```python
from app.components.core.trigger import PollingTrigger
from app.components.core.updater import UpdateFrequency
from app.components.display.base_apps.clock import DateTimeApp

clock = DateTimeApp()  # Uses its default 10-second interval trigger
static_clock = DateTimeApp(trigger_factory=None)
polling_clock = DateTimeApp(
    trigger_factory=lambda callback: PollingTrigger(
        callback,
        frequency=UpdateFrequency(seconds=0.1),
        evaluation=lambda: True,
        cooldown=UpdateFrequency(seconds=5),
    ),
)
```

Before activating a display app, supply its display information, resolver, and
output function. This static example runs without hardware:

```python
from app.components.display.base_apps.static import StaticDisplayItem
from control.source.display_controller import DisplayInfo

outputs = []
item = StaticDisplayItem(
    "Example", {(1, 1): 3}, needs_resolving=False,
)
item.add_display_info(DisplayInfo(rows=3, columns=15, modules=[]))
item.add_resolve_function(lambda flaps: flaps)
item.add_display_function(outputs.append)
item.activate()
print(outputs)  # [{(1, 1): 3}]
item.deactivate()
```

Static items have no `from_json` or `from_dict` loaders. Construct them directly
with a flap map. `DisplayPlaylist` also has no JSON loader. Configuration loading
and the API's legacy frequency fields remain separate integration work.

Verify the examples and triggers without hardware or weather network requests:

```bash
cd software
../.venv/bin/python -m unittest app.components.test.test_playlist app.components.test.test_display_playlist app.components.test.test_example_apps app.components.test.test_display_item -v
../.venv/bin/python -m unittest discover -s app/components/test -p 'test_*trigger.py' -v
```
