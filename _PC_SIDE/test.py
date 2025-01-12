import socket

class Client:
    def __init__(self, host: str, port: int, commands: dict):
        """
        Initialize the client with server details and predefined commands.
        :param host: The server's IP address.
        :param port: The server's port number.
        :param commands: A dictionary of hardcoded commands.
        """
        self.host = host
        self.port = port
        self.commands = commands
        self.socket = None

    def connect(self):
        """Establish a connection to the server."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((self.host, self.port))
            print(f"Connected to server at {self.host}:{self.port}")
        except ConnectionError as e:
            print(f"Failed to connect: {e}")
            self.socket = None

    def send_message(self, message: str) -> str:
        """
        Send a message to the server and return the response.
        :param message: The message to send.
        :return: The server's response.
        """
        if not self.socket:
            raise ConnectionError("Not connected to the server.")
        
        try:
            self.socket.sendall(message.encode())
            response = self.socket.recv(1024)
            return response.decode()
        except Exception as e:
            print(f"Error during communication: {e}")
            return "Error"

    def close(self):
        """Close the connection to the server."""
        if self.socket:
            self.socket.close()
            print("Connection closed.")

    def run(self):
        """Run the client interactively with hardcoded commands or custom input."""
        if not self.socket:
            print("Client is not connected. Please connect first.")
            return

        try:
            while True:
                # List hardcoded commands
                print("\nAvailable commands:")
                for key, command in self.commands.items():
                    print(f"  {key}: {command}")
                print("  custom: Type your custom message")
                print("  exit: Quit the client")

                # User choice
                choice = input("\nEnter your choice: ").lower()
                if choice == 'exit':
                    print("Exiting...")
                    break
                elif choice == 'custom':
                    message = input("Enter your custom message: ")
                elif choice in self.commands:
                    message = self.commands[choice]
                else:
                    print("Invalid choice. Try again.")
                    continue

                # Send the message and print the response
                response = self.send_message(message)
                print(f"Server response: {response}")

        finally:
            self.close()


if __name__ == "__main__":
    COMMANDS = {
        "hello": "HELLO_SERVER",
        "tool_number": 5,
        "user_follow_enabled": True,
        "tool_name": "marteau"
    }

    client = Client(host="192.168.1.1", port=5000, commands=COMMANDS)
    client.connect()
    client.run()
