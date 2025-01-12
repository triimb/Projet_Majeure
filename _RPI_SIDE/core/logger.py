import logging

def setup_logger(log_path: str) -> None:
    """
    Configures the logging setup.

    :param log_path: Path to the log file.
    """
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d %b %Y %H:%M:%S",
    )



def clean_log_file(log_path: str) -> None:
    """
    Clears the log file content.

    :param log_path: Path to the log file.
    """
    with open(log_path, "w"):
        pass