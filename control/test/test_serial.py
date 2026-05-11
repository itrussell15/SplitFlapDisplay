import serial
import time

# Configuration - Change '/dev/ttyACM0' to your specific port
SERIAL_PORT = '/dev/ttyACM0' 
BAUD_RATE = 9600
TIMEOUT = 2  # Seconds to wait for a response

def interact_with_arduino():
    try:
        # Initialize Serial Connection
        print(f"Connecting to {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
        
        # 1. THE RESET DELAY
        # Arduinos reset when the serial port opens. 
        # We must wait for the bootloader to finish.
        print("Waiting for Arduino to reboot...")
        time.sleep(2) 
        
        # 2. SEND DATA
        message = b'\x02\x01\x01\xff\x00\xff\x03'
        print(f"Sending: '{message}'")
        # ser.write(message.encode('utf-8'))
        ser.write(message)
        
        # 3. WAIT FOR THE WINDOW
        # Since the Arduino reads for 1 second, we should wait 
        # slightly longer than that before expecting the full response.
        print("Waiting for Arduino's 1-second window to close...")
        time.sleep(1.2)
        
        # 4. READ RESPONSE
        if ser.in_waiting > 0:
            # readlines() or read_until() works well here
            # response = ser.readline().decode('utf-8').strip()
            response = ser.readline().strip()
            print(f"Arduino response: {response}")
        else:
            print("No response received.")

        # Clean up
        ser.close()
        print("Connection closed.")

    except serial.SerialException as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    interact_with_arduino()