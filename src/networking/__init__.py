# Import for side effects
from mods_base.mod_list import base_mod

from . import (
    queue,  # noqa: F401  # pyright: ignore[reportUnusedImport]
    transmission,  # noqa: F401  # pyright: ignore[reportUnusedImport]
)
from .decorators import NetworkFunction, broadcast, host, targeted
from .factory import add_network_functions, bind_all_network_functions

__all__: tuple[str, ...] = (
    "__author__",
    "__version__",
    "__version_info__",
    "add_network_functions",
    "bind_all_network_functions",
    "broadcast",
    "host",
    "NetworkFunction",
    "targeted",
)

__version_info__: tuple[int, int] = (1, 0)
__version__: str = f"{__version_info__[0]}.{__version_info__[1]}"
__author__: str = "bl-sdk"

"""
This module allows you to perform some basic message passing between players. After decorating a
function appropriately, you simply call it like any other, and this module will take care of
automatically forwarding it and it's args, so that it executes on the correct player. The function
will not execute locally if the local player isn't a target.


The decorator you need to use is composed of two parts: the destination, and the message type.

The destination decides where the function is run:
- broadcast: Runs the function on all connected players.
- host: Only runs the function on the host.
- targeted: Only runs the function on a specific player. Using one of these decorators prepends a
            position only argument, to which you must pass the PlayerReplicationInfo object of the
            specific player you want it to run on.

The message type determines what args the function supports:
- message: No args. This redirects to whatever message type is most efficient.
- json_message: Takes an arbitrary number of json-encodable arguments. **This is not type checked!**
- string_message: Takes a single string argument.

When using a decorator, the destination is the outer namespace, the message type comes after it. As
an example, if you wanted to send the host an int, you'd want the host destination and json message
type, so you'd decorate your function using @host.json_message.


While a network function is being executed, you can retrieve who sent the message using the 'sender'
field added to it. This is the sender's PlayerReplicationInfo object. If you're running on the host,
you can retrieve the relevant PlayerController using func.sender.Owner. If you're a client, the
controller may not be available. This field is undefined once the function finishes - though note
that it's type hinted as always returning an object for convenience.


After defining all your network functions, you still need to enable them alongside your mod. You'll
generally want to do this by calling add_network_functions() right after registering your mod, which
automatically scans for all network functions and hooks them up correctly.

```
@host.json_message
def my_function(value: int) -> None:
    pass

mod = build_mod()
add_network_functions(mod)
```

Alternatively, the decorators add enable/disable methods to each network function, which you can
call manually.

When used on a method, the decorators essentially create a factory. You MUST bind it to a specific
instance before using it further - see NetworkFunction.bind() or bind_all_network_functions(). This
is done automatically on the mod object during add_network_functions().

Every network function uses a unique identifier to work out what to call on the remote side. By
default, binding a method copies the identifier - which may cause issues if you have multiple
instances active at the same time. If you're doing this, you MUST provide each with a unique, but
replicateable (no using id(self)), identifier extension when binding them, to prevent them from
getting mixed up.


Network functions are generally guaranteed to be reliable, they'll always make their way to the
other players, and always in the same order as they were called locally. However, the engine imposes
a maximum bandwidth limitation, and when this is exceeded, messages are silently dropped. There is
no built in handling for this. If you're trying to send particularly large amounts of data, try
splitting it across multiple calls, the amount of messages per tick is deliberately limited to try
avoid running into this bandwidth limit.


This module deliberately exposes a rather small public interface. It's all been covered above, but
to put it all into one list:

@broadcast.message
@broadcast.json_message
@broadcast.string_message
@host.message
@host.json_message
@host.string_message
@targeted.message
@targeted.json_message
@targeted.string_message

NetworkFunction
NetworkFunction.__wrapped__
NetworkFunction.network_identifier
NetworkFunction.sender
NetworkFunction.enable()
NetworkFunction.disable()
NetworkFunction.bind()
NetworkFunction.__call__

add_network_functions()
bind_all_network_functions()

Anything else is subject to change if/when we come up with better methods of transmitting data.
"""


base_mod.components.append(base_mod.ComponentInfo("Networking", __version__))
