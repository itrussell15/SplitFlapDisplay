# Split-Flap Display

Forked from [Adam G Makes - SplitFlapDisplay](https://github.com/adamgmakes/split-flap-display)

## Background
I had long been obsessed with split flap displays, but the price point for something like a [Vestaboard](https://www.vestaboard.com/note) made it feel not feasible for some decor in my house. So I decided to spend more money AND time on it by trying to make it myself.

Seeing Adam G's [youtube video](https://www.youtube.com/watch?v=-C8_AtxEEQc) and longing for a new challenge, I decided to make it. I had previously thought about trying to make one of these, but the biggest barrier for entry was the hardware design. Which Adam absolutely crushed with this modular system with really accessible components.

The thing that I wanted to improve on was the software. I wanted to re-write the firmware and orchestration in a more modular way.

## Hardware
[Adam's ReadMe](https://github.com/adamgmakes/SplitFlapDisplay/blob/main/README.md) and repo has the playbook on how to make all the parts, what to buy, what to order, all those nitty gritty details. I am mainly going to focus on what I changed in this document.

If you want access to be able to talk to the man himself, Adam has a [Patreon](https://www.patreon.com/cw/AdamGMakes) that he seems to be pretty active in and happy to answer questions about how he did things.

## Software
### Design
I wanted the main controller to be doing a lot of the heavy lifting and coordinating what module should do what. The module would be more naive and do simple things like move to certain steps and be able to home itself. I also wanted to abstract away the idea of what the flap had on it from the module side simply have the module be able to move to "positions" that would corelate with a given flap. They are basically the same thing, but allows more flexibility for changing in what is actually being shown on the flap.

#### Serial Processing
The ability to have a non-blocking way of processing serial commands as they are being generated for moves was also interesting to me so that I could try and send data as fast as possible. The bus that commands is being sent across is probably our biggest latency bottleneck and I wanted to be able to keep that as active as possible.

This led me to make a `SerialProcessor` class that would simply spin up a thread and listen for messages to be added to a queue. When a message is added, it would be encoded, shipped off and wait for a response. This would allow us to add commands in a non-blocking way, but still ensure that data is being sent in a clean way and avoid collisions.


### Controller

A `BusController` was made to control any modules that are attached to a single bus. Any USB to RS485 connection to a bus board must have its own `BusController` to handle the communication, but if your setup is similar to what Adam has, a single USB to RS485 device hooked to all the buses, then you will only need a single `BusController`. This will aggregate all the modules on the bus and handle the communication across serial to them. It is able to discover devices by sending the `discover()` command, where it pings every possible address that a module could have an sees which ones respond. This will automatically configure your bus controller and subscribe all the found modules to its command queue.

### Module

The `ModuleController` is a bit of a misnomer as it actually doesn't really control anything at all. It has no bindings to any physical hardware. It simply subscribes to the `BusController`'s command queue and is able to add commands for its module if any of its APIs are called. After the command is processed, any respones from its module will be funneled back to it, where it can update the state of that module on the controller side.

## Firmware

### Calibration
As I mentioned in the design section, I wanted to have modules simply know what a "position" is and not what is actually being displayed. So I would need to correlate motor steps to those positions that would display whatever you want. In Adam's video, he mentioned that a large pain point when setting everything up was to calibrate each module to display the desired flap when he wanted it. This required some fine tuning and I really think I only have patience to do that once, so I wanted to take advantage of the EEPROM in the microcontroller to store persistent memory of these positions so I don't have to redo it every time the module loses power.

The step value for a given position is stored in a 2 byte memory location 2-65 in the EEPOM, where 0-1 are reserved for storing the module's row and column location.

### Commands
Here are all the currently supported commands in the firmware, where the value is the number being sent in the packet.
```
enum Command {
  CMD_PING = 0,
  CMD_HOME = 1,
  CMD_STOP = 2,
  CMD_GET_POSITION = 3,
  CMD_SET_POSITION = 4,
  CMD_MOVE_TO_POSITION = 5,
  CMD_GET_SPEED = 6,
  CMD_SET_SPEED = 7,
  CMD_GET_STEPS = 8,
  CMD_MOVE_TO_STEP = 9
};
```

### Communications
The firmware was also refactored to use the new communication protocol that is outlined below

## Communications

The communication between the controller and the modules is done along a shared bus using a [half duplex](https://en.wikipedia.org/wiki/Duplex_(telecommunications)#Half_duplex) with RS485. This requires only a single device to be talking on the bus at a time or we will run into collisions (or data being sent on the bus at the same time). So the communication process currently looks like this:
1. Controller sends a packet with an address for a single module along the bus
1. If there is a module on the bus with that address, then process the packet, otherwise ignore it.

> There is a potential for using a "broadcast" packet, which all devices would accept and process.

### Controller
The controller is the brains of the operation

### Module Packets
This is the packet that comes out of the Raspberry Pi (or other controller) and into the modules via the bus. These packets have the following structure:
| Position | # Bytes | Description |
|-|-|-|
|Start Value | 1 | Fixed value byte to signal that this is the start of a packet |
|Module Row | 1 | The row that the target module lives on |
|Module Column | 1 | The column that target module lives on |
|Sequence ID | 1 | Sequence value assigned when packet gets put into queue |
|Command Value | 1 | Command that is being sent to the module |
|Data Value | 2 | Payload associated with command |
|Checksum | 1 | Checksum of all value besides this one and start and end values  |
|End Value | 1 | Fixed value byte to signal that this is the end of a packet |
> 9 bytes total

### Controller Packets
This is the packet that comes out of the a module and responds to the controller. These packets have the following structure:
| Position | # Bytes | Description |
|-|-|-|
|Start Value | 1 | Fixed value byte to signal that this is the start of a packet |
|Module Row | 1 | The row that this module lives on |
|Module Column | 1 | The column that this module lives on |
|Sequence ID | 1 | The sequence value that the module is responding to |
|Command Value | 1 | Command that the module is responding to |
|Data Value | 2 | Payload associated with command |
|Status | 1 | Whether the command was successful or not |
|Checksum | 1 | Checksum of all value besides this one and start and end values  |
|End Value | 1 | Fixed value byte to signal that this is the end of a packet |
> 10 bytes total

Total size of a call and response from the controller to a module is 19 bytes and takes roughly 0.05ms to send, process and respond at a baudrate of 9600. This could lead to some high latency from the first modules movement to the last modules movement (~2.25 seconds for 45 modules). So I am investigating ways to make these communcations faster.

### Ideas/Investigations
- The controller packet may be a little bit overkill and can potentially be reduced to transmit less data, but I wanted a robust solution to ensure that packets are being received and executed properly. It may be worth investigating if smaller ones can be sent because smaller packets mean quicker communications and quicker communications means more responsiveness when you send commands to the display.
- Using multiple RS485 controllers to be able to isolate each row into its own bus, this would limit the latency to just the number of modules that you have on that column. Which for this project, it would theoretically reduce it to 0.75 seconds.
- Send a "queuing" command that will tell which position the module should move to when it receives the go-ahead, and then broadcast a move command to all modules.
  - This doesn't get around the communication latency, but it will make all the modules synchronized and moving at the same time.
---

## Idea Wishlist
I am storing ideas of things that I would like to do at some point here for reference.

- [ ] Create a dockerized app that is web-accessible and can control the display
- [ ] Create "mock" hardware that will allow people to develop on the system without needing access to hardware



## License

This project is licensed under [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/).

You are free to share and adapt this project for non-commercial purposes, as long as you give appropriate credit to Adam G Makes and distribute any derivatives under the same license.
