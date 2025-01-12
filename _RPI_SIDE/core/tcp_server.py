"""
TCP Server module for handling incoming and outgoing data using queues.
"""

import socket
import logging
from abc import ABC, abstractmethod
import threading
import json

class TcpServer(ABC):
    """
    Abstract TCP Server to handle incoming and outgoing data.
    """

    def __init__(self, host: str, port: int):
        """
        Initialize the TCP server.

        :param host: Host IP address to bind the server.
        :param port: Port to bind the server.
        """
        self.host = host
        self.port = port
        self.server_socket: socket.socket | None = None
        self.running = False

    @abstractmethod
    def handle_client_data(self, data: dict) -> None:
        """
        Abstract method to handle incoming data from a client.

        :param data: Data received from the client in {key: value} format.
        """
        pass

    @abstractmethod
    def send_data_to_client(self) -> dict | None:
        """
        Abstract method to provide data to send to the client in {key: value} format.
        
        :return: Data to send in {key: value} format or None if no data is available.
        """
        pass

    def start_server(self) -> None:
        """
        Start the TCP server.
        """
        logging.info("Starting TCP server...")

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            logging.info(f"TCP Server listening on {self.host}:{self.port}")
        except Exception as e:
            logging.error(f"Failed to start the TCP Server: {e}")
            return

        self._server_loop()

    def _server_loop(self) -> None:
        """
        Main server loop to handle client connections.
        """
        while self.running:
            try:
                logging.info("Waiting for a client to connect...")
                connection, client_address = self.server_socket.accept()
                logging.info(f"Client connected: {client_address}")

                self._handle_client(connection, client_address)

            except Exception as e:
                logging.error(f"Error in server loop: {e}")

    def _handle_client(self, connection: socket.socket, client_address: tuple[str, int]) -> None:
        """
        Handle communication with a connected client.

        :param connection: Client socket connection.
        :param client_address: Address of the connected client.
        """
        try:
            while self.running:
                data = connection.recv(1024)

                if not data:
                    logging.warning(f"Client {client_address} disconnected.")
                    break

                decoded = data.decode().strip()
                logging.info(f"[TCP Server] Received from {client_address}: {decoded}")

                try:
                    # Parse JSON-formatted data
                    data_dict = json.loads(decoded)
                    if isinstance(data_dict, dict) and len(data_dict) == 1:
                        self.handle_client_data(data_dict)
                    else:
                        logging.warning(f"Invalid data format received: {decoded}")
                except json.JSONDecodeError:
                    logging.warning(f"Failed to parse JSON: {decoded}")

                # Prepare outgoing data
                response_dict = self.send_data_to_client()
                if response_dict:
                    try:
                        response_json = json.dumps(response_dict)
                        connection.sendall(response_json.encode())
                        logging.info(f"[TCP Server] Sent to {client_address}: {response_json}")
                    except Exception as e:
                        logging.error(f"Failed to send data to {client_address}: {e}")

        except Exception as e:
            logging.error(f"Error handling client {client_address}: {e}")

        finally:
            logging.info(f"Closing connection with {client_address}...")
            connection.close()

    def stop_server(self) -> None:
        """
        Stop the TCP server.
        """
        logging.info("Stopping TCP server...")
        self.running = False

        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        logging.info("TCP server stopped.")
