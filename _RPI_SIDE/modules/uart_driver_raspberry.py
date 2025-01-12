"""UART Driver Implementation for Raspberry Pi and STM32 Screen Communication."""

from typing import Optional
import logging
import serial
import time
from multiprocessing import Queue
from core.uart_manager import UartInterface, MessageType, ArmState, ScreenError
from configs.settings import UART_BAUDRATE, UART_TIMEOUT, RFID_UID
from enum import Enum

"""
TO DO:
- ARM State sending and logic
- Joystick Direction Sending
- Speed Sending
"""

class MessageField(Enum):
    """ Enum for the different types of messages that can be sent to the STM32. """
    
    TOOL_NUMBER = "tool_number"
    TOOL_NAME = "tool_name"
    USER_FOLLOW_ENABLED = "user_follow_enabled"
    JOYSTICK_DIRECTION = "joystick_direction"
    SPEED = "speed"
    IS_RFID_VALID = "is_rfid_valid"
    ARM_MOVEMENT = "arm_movement"
    BATTERY_LEVEL = "battery_level"

class UartDriverRaspberry(UartInterface):
    """Concrete implementation of the UARTInterface using `/dev/serial0` on Raspberry Pi."""

    def __init__(
            self,
            to_stm32_queue: Queue,
            to_pc_queue: Queue, 
            port='/dev/serial0', 
            baudrate=UART_BAUDRATE, 
            timeout=UART_TIMEOUT
        ):

        super().__init__()
        self.to_stm32_queue = to_stm32_queue
        self.to_pc_queue = to_pc_queue
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
        except serial.SerialException as e:
            raise RuntimeError(f"Failed to initialize UART on port {self.port}: {e}")

        logging.info(f"UART initialized on {self.port} with baudrate {self.baudrate}")

    def io_send_uart(self, uart_bytes: bytes) -> bool:
        """
        Send the given bytes to the screen STM32 via UART.

        :param uart_bytes: UART Frame bytes to be sent
        :type uart_bytes: bytes
        :return: True if uart was sent successfully, False otherwise
        """
        try:
            self.serial.write(uart_bytes)
            self.serial.flush()
            logging.debug(f"Sent UART frame: {uart_bytes.hex()}")
            return True
        except serial.SerialException as e:
            logging.error(f"Failed to send UART frame: {e}")
            return False

    def io_bytes_received(self, rx_bytes: bytes) -> None:
        """
        Handles incoming bytes from the UART interface.

        :param rx_bytes: Received bytes from UART
        :type rx_bytes: bytes
        """
        logging.debug(f"Received UART bytes: {rx_bytes.hex()}")
        super().io_bytes_received(rx_bytes)

    def cb_rfid_received(self, rfid: str) -> None:
        """
        Called when a new RFID tag is detected.

        :param rfid: RFID in lowercase hex format [0-9a-f]{12}
        :type rfid: str
        """
        logging.info(f"RFID detected: {rfid}")

        # This logic will block the robot if an incorrect RFID is scanned after it has been unlocked with the correct one.
        # Only the valid RFID can unlock the robot
        if rfid == RFID_UID:
            self.to_stm32_queue.put({MessageField.IS_RFID_VALID: True})
            self.to_pc_queue.put({MessageField.IS_RFID_VALID: True})
        else:
            self.to_stm32_queue.put({MessageField.IS_RFID_VALID: False})
            self.to_pc_queue.put({MessageField.IS_RFID_VALID: False})

    
    def cb_battery_level(self, level: int) -> None:
        """
        Called when the system's battery level has changed.

        :param level: Battery level 0 for 0% and 255 for 100%
        :type level: int
        """
        logging.info(f"Battery level changed: {level}%")

        # Convert the battery level to a percentage between 0% and 100%
        converted_battery_level = (level / 255) * 100

        self.to_pc_queue.put({MessageField.BATTERY_LEVEL: converted_battery_level})

    def cb_arm_state(self, state: ArmState) -> None:
        """
        Called when the robot arm state has changed.

        :param state: Robot arm state
        :type state: ArmState
        """
        logging.info(f"Arm state changed: {state.name}")

        # TODO : See with Antoine

    def _send_next_message_from_queue(self, message: dict) -> None:
        """
        Send message depending on his field in MessageField.

        :param message: Message to be sent to the STM32
        :type message: dict
        :return: UART frame bytes
        """

        message_type = next(iter(message))
        message_value = message[message_type]

        if message_type == MessageField.TOOL_NUMBER:
            super().set_tool_id(message_value)
        elif message_type == MessageField.TOOL_NAME:
            super().set_tool_name(message_value)
        elif message_type == MessageField.USER_FOLLOW_ENABLED:
            super().follow_mode_enable(message_value)
        elif message_type == MessageField.JOYSTICK_DIRECTION:
            ...
        elif message_type == MessageField.SPEED:
            ...
        elif message_type == MessageField.IS_RFID_VALID:
            super().is_rfid_valid(message_value)
        elif message_type == MessageField.ARM_MOVEMENT:
            ...
        else:
            logging.error(f"Unknown message type: {message_type}")

    def start(self):
        """
        Starts the UART communication loop. Placeholder for your implementation.
        """
        logging.info("UART communication started.")
        pass

    def stop(self):
        """
        Stops the UART communication. Placeholder for your implementation.
        """
        logging.info("UART communication stopped.")
        self.serial.close()

    def run(self):
        """
        Main loop for processing UART communication. Placeholder for your implementation.
        """
        logging.info("Running main UART loop.")
        while True:
            # Receive any incoming UART data
            if self.serial.in_waiting:
                rx_data = self.serial.read(self.serial.in_waiting)
                self.io_bytes_received(rx_data)

            # Sending data to STM32 if there are messages in the queue
            if not self.to_stm32_queue.empty():
                message = self.to_stm32_queue.get()
                self._send_next_message_from_queue(message)


            # time.sleep(0.01)
