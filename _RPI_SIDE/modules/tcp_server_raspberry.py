from queue import Queue
from core.tcp_server import TcpServer
import socket
import logging
from configs.settings import TCP_SERVER_HOST, TCP_SERVER_PORT

class TcpServerRaspberry(TcpServer):
    """
    Concrete implementation of the TcpServer for the project, using queues for communication.
    """

    def __init__(self, host: str = TCP_SERVER_HOST, port: int = TCP_SERVER_PORT, to_stm32_queue: Queue = Queue(), to_pc_queue: Queue = Queue()):
        """
        Initialize the concrete TCP server.

        :param host: Host IP address to bind the server.
        :param port: Port to bind the server.
        :param to_stm32_queue: Queue for commands heading to STM32.
        :param to_pc_queue: Queue for commands heading to the PC.
        """
        super().__init__(host, port)
        self.to_stm32_queue = to_stm32_queue
        self.to_pc_queue = to_pc_queue

    def handle_client_data(self, data: dict) -> None:
        """
        Handle incoming data from the client.

        :param data: Data received from the client in {key: value} format.
        """
        logging.info(f"[TcpServerConcrete] Handling client data: {data}")
        self.to_stm32_queue.put(data)

    def send_data_to_client(self) -> dict | None:
        """
        Get data to send to the client in {key: value} format.

        :return: Data to send or None if no data is available.
        """
        if not self.to_pc_queue.empty():
            return self.to_pc_queue.get()
        return None
