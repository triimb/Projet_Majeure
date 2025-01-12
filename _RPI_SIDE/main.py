"""
This file handles multiprocessing and processes to start the program.
"""

from core.logger import setup_logger, clean_log_file
from core.hotspot_manager import monitor_connections, disable_hotspot

from modules.tcp_server_raspberry import TcpServerRaspberry
from modules.uart_driver_raspberry import UartDriverRaspberry

from modules.hotspot_monitor import hotspot_routine

from multiprocessing import Process, Queue
import logging
import subprocess
import time
import signal


# Global variables to hold references to processes
tcp_process = None
uart_process = None


def start_robot(to_stm32_queue: Queue, to_pc_queue: Queue) -> None:
    """
    Start both the TCP Server and UART Manager as separate processes.

    :param to_stm32_queue: Queue for commands heading to STM32.
    :param to_pc_queue: Queue for commands heading to the PC.
    """

    global tcp_process, uart_process

    logging.info("Initializing shared resources and starting processes...")

    # FOR ME : daemon=True => process enfants s'exécutent en arrière-plan et se terminent automatiquement lorsque main.py se termine.
    tcp_process = Process(target=start_tcp_server_process, args=(to_stm32_queue, to_pc_queue), daemon=True)
    uart_process = Process(target=start_uart_manager_process, args=(to_stm32_queue, to_pc_queue), daemon=True)

    tcp_process.start()
    uart_process.start()

    # FOR ME : No need for join() here since these are daemon processes and will automatically
    # terminate when the main process exits.
    logging.info("Processes started, continuing with main logic...")



def start_tcp_server_process(to_stm32_queue: Queue, to_pc_queue: Queue) -> None:
    """
    Start the TCP server process.

    :param to_stm32_queue: Queue for commands heading to STM32.
    :param to_pc_queue: Queue for commands heading to the PC.
    """
    logging.info("Starting TCP server process...")
    server = TcpServerRaspberry(to_stm32_queue, to_pc_queue)
    server.start_server()

    try:
        while True:
            time.sleep(1)  # Keep the process alive
    except KeyboardInterrupt:
        logging.info("Stopping TCP server process...")
    finally:
        server.stop_server()


def start_uart_manager_process(to_stm32_queue: Queue, to_pc_queue: Queue) -> None:
    """
    Start the UART manager process.

    :param to_stm32_queue: Queue for commands heading to STM32.
    :param to_pc_queue: Queue for commands heading to the PC.
    """
    logging.info("Starting UART manager process...")
    uart_manager = UartDriverRaspberry(to_stm32_queue, to_pc_queue)
    
    try:
        uart_manager.start()
        uart_manager.run()
    except KeyboardInterrupt:
        logging.info("Stopping UART Manager process...")
    finally:
        uart_manager.stop()


def handle_exit_signal(signum, frame):
    """
    Handle termination signals (e.g., SIGTERM, SIGINT) to shut down processes cleanly.
    """
    logging.info(f"Received termination signal: {signum}. Shutting down processes...")
    global tcp_process, uart_process

    if tcp_process is not None and tcp_process.is_alive():
        tcp_process.terminate()
        tcp_process.join()
        logging.info("TCP Server process terminated.")

    if uart_process is not None and uart_process.is_alive():
        uart_process.terminate()
        uart_process.join()
        logging.info("UART Manager process terminated.")

    logging.info("All processes terminated cleanly. Exiting.")
    exit(0)


def main() -> None:
    """
    Main function to initialize logging, configure hotspot settings,
    and start the robot program.
    """
    log_path: str = "/home/triimb/_ROBOT_PROJECT/logs/robot.log"
    
    clean_log_file(log_path)
    setup_logger(log_path)

    logging.info("Logger initialized. Starting robot program...")

    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_exit_signal)
    signal.signal(signal.SIGINT, handle_exit_signal)

    # Start hotspot routine
    if hotspot_routine():
        logging.info("Hotspot routine completed successfully.")
    else:
        logging.error("Hotspot failed to start. Exiting program.")


    # Initialize shared queues
    to_stm32_queue: Queue = Queue()  # Queue for commands heading to STM32
    to_pc_queue: Queue = Queue()     # Queue for commands heading to the PC

    # Monitor connections and run the robot processes
    try:
        monitor_connections(lambda: start_robot(to_stm32_queue, to_pc_queue))
    except KeyboardInterrupt:
        logging.info("Program interrupted by user.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        logging.info("Cleaning up resources...")
        disable_hotspot()
        logging.info("Program terminated successfully.")


if __name__ == "__main__":
    # Launch a debugging terminal to view logs
    subprocess.Popen(
        ["xterm", "-hold", "-e", "tail -f /home/triimb/_ROBOT_PROJECT/logs/robot.log"],
        start_new_session=True
    )

    main()
