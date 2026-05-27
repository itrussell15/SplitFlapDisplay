# Firmware

## Packets
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

Total size of a call and response from the controller to a module is 19 bytes and takes roughly 23ms to send, process and respond at a baudrate of 9600. This would result in *~1 second* of latency for the whole set of modules (currently planning on 45) using a single serial bus. 
> As I am still working on getting the hardware fully up and running. I am testing this via a "normal" serial port and not a software serial port, so the 23ms time could change as I get further. 

## Commands
The following is a list of commands that are currently (or plan to be) supported in the firmware.

### PING - 1
Command to check the existence of a module at a given position.

### HOME - 2
Starts a homing sequence on the module

### STOP - 3
> This command is not yet supported

### GET POSITION - 4
Gets the step value associated with the requested position

### SET POSITION - 5
Sets the provided position value to the motors current step value

### MOVE TO POSITION - 6

### GET SPEED - 7
> This command is not yet supported

### SET SPEED - 8
> This command is not yet supported

### GET STEPS - 9
Returns the current step value for the stepper motor

### MOVE TO STEP - 10
Moves the motor to the provided step value

### SET STEP TARGET - 11
Stores a target step value to be moved to later with `MOVE_TO_TARGET`

### SET POSITION TARGET - 12
Stores a target position to be moved to later with `MOVE_TO_TARGET`

### MOVE TO TARGET - 13
> Requires a previous call to `SET_POSITION_TARGET` or `SET_STEP_TARGET`
Executes a move to a previously cached target location 

### HALL_EFFECT_STATUS - 14
> This command is not yet supported

Gets the current status of the hall effect sensor. This will return 0 for open, and 1 for closed.

## Error Codes
Below is a list of error codes that can be returned from the module. If you receive a message from the module with a false status value, then there will be an integer value in the data value field that corresponds to one of the following error codes

### BAD CHECKSUM
The checksum received by the module was not valid based on the other values received. 

### COMMAND NOT FOUND
The command value was not recognized by the firmware

### INVALID POSITION
The position value requested to perform an action on was not between 0-64

### INVALID STEP
The step value requested to perform an action on was not between 0-4096