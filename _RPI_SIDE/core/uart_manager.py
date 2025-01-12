"""Communication driver for interacting with the
Screen STM32 over a UART link."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import auto, Enum, IntEnum

_START_BYTE = b'\x8A'
_STOP_BYTE = b'\x51'
_UART_HEADER_LENGTH = 2
_UART_FOOTER_LENGTH = 1
_UART_OVERHEAD_LENGTH = _UART_HEADER_LENGTH + _UART_FOOTER_LENGTH
_UART_MIN_FRAME_LENGTH = _UART_OVERHEAD_LENGTH
_UART_MAX_DATA_LENGTH = 16

MAX_TOOL_ID = 0x7

logger = logging.getLogger("screen_driver")
logger.propagate = True


class ScreenError(Exception):
    """Screen driver base error."""


class PayloadTooLongError(ScreenError):
    """Payload inside frame exceeds UART_MAX_DATA_LENGTH."""

    def __init__(
        self,
        payload_length: int | None = None,
        message: str | None = None
    ) -> None:
        if message is not None:
            self.message = message
        elif payload_length is not None:
            self.message = (f"Payload too long, max payload length allowed is "
                            f"{_UART_MAX_DATA_LENGTH}, given {payload_length}")


class InvalidDataError(ScreenError):
    """Data inside UART frame is invalid."""


class UartError(ScreenError):
    """Error while transmitting UART frame."""


class UartParsingError(ScreenError):
    """Error while parsing UART frame."""


class UnknownMessageTypeError(ScreenError):
    """Frame message type is unknown."""


class InvalidFrameStartError(UartParsingError):
    """Start byte is invalid."""


class InvalidPayloadLengthError(UartParsingError):
    """Payload length is invalid."""


class InvalidFrameEndError(UartParsingError):
    """End byte is invalid."""


class IncompleteFrameError(UartParsingError):
    """Frame is shorter than MIN_FRAME_LENGTH."""


# typedef enum {
#     RPI_ARM_IDLE = 0x01,
#     RPI_ARM_READY = 0x02,
#     RPI_ARM_CLOSED = 0x04,
#     RPI_ARM_DISPLAY = 0x08
# } RPI_ARM_STATE;
class ArmState(IntEnum):
    """State of the robot arm."""
    IDLE = 0x01
    READY = 0x02
    CLOSED = 0x04
    DISPLAY = 0x08

    def to_bytes(self) -> bytes:
        """
        Converts the enum state value to bytes.

        :return: Enum value
        :rtype: bytes
        """
        return self.value.to_bytes(1, byteorder='big')

    def from_bytes(self, value: bytes) -> ArmState:
        """
        Converts bytes to the enum state value.

        :param value: Arm state code
        :type value: bytes
        :return: Arm state enum value
        :rtype: ArmState
        """
        return ArmState(int.from_bytes(value, byteorder='big'))


# typedef enum {
#     // From RPI
#     RPI_TYPE_TOOL_ID = 0x01,
#     RPI_TYPE_TOOL_NAME = 0x02,
#     RPI_TYPE_FOLLOW_MODE_ENABLE = 0x04,
#     RPI_TYPE_VALID_RFID = 0x08,
#     // To RPI
#     RPI_TYPE_BATTERY_LEVEL = 0x81,
#     RPI_TYPE_ARM_STATUS = 0x82,
#     RPI_TYPE_RFID_VALUE = 0x84,
# } RPI_MESSAGE_TYPE;
class MessageType(Enum):
    """UART Frame type identifier"""
    # From RPI
    TOOL_ID = (0x01, False, 1, int)
    TOOL_NAME = (0x02, False, 16, str)
    FOLLOW_MODE_ENABLE = (0x04, False, 1, bool)
    RFID_VALID = (0x08, False, 1, bool)

    # From STM32
    BATTERY_LEVEL = (0x81, True, 1, int)
    ARM_STATUS = (0x82, True, 1, ArmState)
    RFID_VALUE = (0x84, True, 4, str)

    def __init__(
        self,
        code: int,
        from_stm32: bool,
        data_len: int,
        data_type: type
    ):
        self.code: int = code
        self.from_stm32: bool = from_stm32
        self.data_len: int = data_len
        self.data_type: type = data_type

    def to_bytes(self) -> bytes:
        """
        Converts the enum type value to bytes.

        :return: Enum value
        :rtype: bytes
        """
        return self.code.to_bytes(1, byteorder='big')

    @classmethod
    def from_bytes(cls, value: bytes) -> MessageType:
        """
        Converts bytes to the enum type value.

        :param value: Type code
        :type value: bytes
        :return: Type enum value
        :rtype: MessageType
        """
        for enum_entry in cls:
            if enum_entry.code == int.from_bytes(value, byteorder='big'):
                return enum_entry
        raise ValueError(f"Unknown message type: {value}")


class UartInterface(ABC):
    """
    Abstract class implementing the Screen STM32 UART interface.
    This class should not be instantiated directly but inherited from.

    Child classes should implement the callback methods denoted `cb_*(...)`
    as well as IO methods denoted `io_`.
    """

    class _ParserState(Enum):
        IDLE = auto()
        READING_HEADER = auto()
        READING_DATA = auto()
        READING_FOOTER = auto()

    def __init__(self):
        self._rx_buff: bytearray = bytearray()
        self._bytes_left: int = 0
        self._parser_state: UartInterface._ParserState = self._ParserState.IDLE

    def set_tool_id(self, tool: int) -> None:
        """
        Changes the selected tool to the specified ID.

        :param tool: Tool ID in the range (0, MAX_TOOL_ID).
        :type tool:
        :raises: UartError if failed to send UART frame
        """
        if not 0 < tool < MAX_TOOL_ID:
            raise InvalidDataError(
                f"Tool ID is out of range (0, {MAX_TOOL_ID}): {tool}"
            )

        data: bytes = bytes([tool])
        frame: bytes = self._format_uart(MessageType.TOOL_ID, data)
        if not self.io_send_uart(frame):
            raise UartError()

    def set_tool_name(self, name: str) -> None:
        """
        Sets the displayed tool name.

        :param name: Tool name (in alphanumeric format)
        :type name: str
        :raises: UartError if failed to send UART frame
        """
        if not name.isalnum():
            raise InvalidDataError(
                "Tool name should only contain alphanumeric characters"
            )

        data: bytes = name.ljust(16, ' ').encode("ascii")
        frame: bytes = self._format_uart(MessageType.TOOL_NAME, data)
        if not self.io_send_uart(frame):
            raise UartError()

    def is_rfid_valid(self, valid: bool) -> None:
        """
        Indicates if the received RFID is valid.

        :param valid: RFID Validity
        :type valid: bool
        :raises: UartError if failed to send UART frame
        """
        data: bytes = bytes([1 if valid else 0])
        frame: bytes = self._format_uart(MessageType.RFID_VALID, data)
        if not self.io_send_uart(frame):
            raise UartError()

    def follow_mode_enable(self, enabled: bool) -> None:
        """
        Enables/disables user following mode.

        :param enabled: Should the follow mode be enabled
        :type enabled: bool
        :raises: UartError if failed to send UART frame
        """
        data: bytes = bytes([1 if enabled else 0])
        frame: bytes = self._format_uart(MessageType.FOLLOW_MODE_ENABLE, data)
        if not self.io_send_uart(frame):
            raise UartError()

    @staticmethod
    def _format_uart(msg_type: MessageType, data: bytes) -> bytes:
        if len(data) > _UART_MAX_DATA_LENGTH:
            raise PayloadTooLongError(len(data))

        if msg_type not in MessageType:
            raise UnknownMessageTypeError(msg_type)

        if len(data) != msg_type.data_len:
            raise InvalidDataError(
                f"Invalid data length: {len(data)} (expected {msg_type.data_len})"
            )

        return _START_BYTE + msg_type.to_bytes() + data + _STOP_BYTE

    def _dispatch_callback(self, msg_type: MessageType, data: bytes) -> None:
        if not msg_type.from_stm32:
            return

        if msg_type == MessageType.RFID_VALUE:
            rfid: str = data.hex()
            self.cb_rfid_received(rfid)
        elif msg_type == MessageType.ARM_STATUS:
            try:
                state: ArmState = ArmState(data[0])
            except ValueError:
                raise InvalidDataError(f"Invalid ARM state: {data[0]}")
            self.cb_arm_state(state)
        elif msg_type == MessageType.BATTERY_LEVEL:
            self.cb_battery_level(data[0])

    def _parse_frame(self, frame: bytes) -> None:
        if len(frame) < _UART_MIN_FRAME_LENGTH:
            raise IncompleteFrameError(
                f"Frame too short: {len(frame)} (expected {_UART_MIN_FRAME_LENGTH})"
            )
        if frame[0].to_bytes(1, byteorder='big') != _START_BYTE:
            raise InvalidFrameStartError(
                f"Invalid start byte: {frame[0].to_bytes(1, byteorder='big')} "
                f"(expected {_UART_MIN_FRAME_LENGTH})"
            )
        if frame[-1].to_bytes(1, byteorder='big') != _STOP_BYTE:
            raise InvalidFrameEndError(
                f"Invalid end byte: {frame[-1].to_bytes(1, byteorder='big')} "
                f"(expected {_UART_MIN_FRAME_LENGTH})"
            )

        try:
            msg_type = MessageType.from_bytes(frame[1].to_bytes(1, byteorder='big'))
        except ValueError:
            raise UnknownMessageTypeError(frame[1])

        data : bytes = frame[_UART_HEADER_LENGTH : - _UART_FOOTER_LENGTH]

        if msg_type.data_len != len(data):
            raise InvalidPayloadLengthError(len(frame))

        self._dispatch_callback(msg_type, data)

    def _store_rx_byte(self, byte: bytes) -> None:
        self._rx_buff += byte
        self._bytes_left -= 1

    def _process_rx_byte(self, byte: bytes) -> None:
        if self._bytes_left > 0:
            self._store_rx_byte(byte)

        if self._parser_state == self._ParserState.IDLE:
            if byte == _START_BYTE:
                self._bytes_left = _UART_HEADER_LENGTH
                self._parser_state = self._ParserState.READING_HEADER
                self._store_rx_byte(byte)

        elif self._parser_state == self._ParserState.READING_HEADER:
            if self._bytes_left == 0:
                try:
                    self._bytes_left = MessageType.from_bytes(byte).data_len
                except ValueError:
                    logger.warning("Invalid message type: %s", byte)
                    self._bytes_left = 0
                self._parser_state = self._ParserState.READING_DATA

        elif self._parser_state == self._ParserState.READING_DATA:
            if self._bytes_left == 0:
                self._bytes_left = _UART_FOOTER_LENGTH
                self._parser_state = self._ParserState.READING_FOOTER

        elif self._parser_state == self._ParserState.READING_FOOTER:
            if self._bytes_left == 0:
                self._parser_state = self._ParserState.IDLE
                self._parse_frame(self._rx_buff)

    def io_bytes_received(self, rx_bytes: bytes) -> None:
        """
        Should be called when new UART data is received.
        Will trigger one of the associated callbacks if correct or
        raise an exception.

        :param rx_bytes: Received bytes from UART
        :type rx_bytes: bytes
        """
        for byte in rx_bytes:
            self._process_rx_byte(byte.to_bytes(1, byteorder="big"))

    @abstractmethod
    def io_send_uart(self, uart_bytes: bytes) -> bool:
        """
        Send the given bytes to the screen STM32 via UART.

        :param uart_bytes: UART Frame bytes to be sent
        :type uart_bytes: bytes
        :return: True if uart was sent successfully
        """
        raise NotImplementedError(
            "This method must be implemented by the class' children"
        )

    @abstractmethod
    def cb_rfid_received(self, rfid: str) -> None:
        """
        Called when a new RFID tag is detected.
        Should trigger an ID verification step, the validity of this RFID
        should be sent back using rfid_verify(bool).

        :param rfid: RFID in lowercase hex format [0-9a-f]{12}
        :type rfid: str
        """
        raise NotImplementedError(
            "This method must be implemented by the class' children"
        )

    @abstractmethod
    def cb_battery_level(self, level: int) -> None:
        """
        Called when the system's battery level has changed.

        :param level: Battery level 0 for 0% and 255 for 100%
        :type level: int
        """
        raise NotImplementedError(
            "This method must be implemented by the class' children"
        )

    @abstractmethod
    def cb_arm_state(self, state: ArmState) -> None:
        """
        Called when the robot arm state has changed.

        :param state: Robot arm state
        :type state: ArmState
        """
        raise NotImplementedError(
            "This method must be implemented by the class' children"
        )
