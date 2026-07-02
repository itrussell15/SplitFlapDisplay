import time
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from control.source.serial_processor import SerialControl
from control.source.dataclasses_ import OutgoingMessage
from utils import create_logger

# Configure the serial connection
# Update 'COM3' or '/dev/cu.usbmodem1101' to match your actual serial device
SERIAL_PORT = '/tmp/vcom_firmware' 
BAUD_RATE = 19200

logger = logging.getLogger(f"MockFirmware({SERIAL_PORT})")

def run_echo_loop():
    try:
        # Initialize serial connection
        ser = SerialControl(SERIAL_PORT, BAUD_RATE)
        ser.connect()
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")
        
        while True:
            # Check if there is data waiting in the serial buffer
            if ser.is_data_waiting:
                # Read the incoming data
                data = ser.read(ser.data_waiting_size)
                logger.debug(f"Heard: {data}")
                message = OutgoingMessage.decode(data)
                logger.info(f"Incoming Message: {message}")
                
                
                # Optional: Send it back out to the device
                # ser.write(data) 
                
            time.sleep(0.01) # Small sleep to prevent CPU spiking
            
    except serial.SerialException as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("Stopping echo loop...")
    finally:
        # if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    create_logger()
    run_echo_loop()