import os
import time
import subprocess
import logging
from typing import Optional

DHCP_LEASES_FILE: str = "/var/lib/misc/dnsmasq.leases"
WIFI_INTERFACE: str = "wlan0"
HOTSPOT_SERVICES: list[str] = ["hostapd", "dnsmasq", "systemd-networkd"]

def execute_command(
    command: list[str], 
    description: str, 
    success_msg: str, 
    error_msg: str
) -> Optional[subprocess.CompletedProcess]:
    """
    Utility function to execute shell commands with logging.

    :param command: List of command arguments to execute.
    :param description: Description of the action for logging.
    :param success_msg: Success message to log if the command executes successfully.
    :param error_msg: Error message to log if the command fails.
    :return: CompletedProcess if the command succeeds, None otherwise.
    """
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logging.info(success_msg)
        return result
    except subprocess.CalledProcessError as e:
        logging.error(f"{error_msg}: {e.stderr.strip()}")
        return None
    except Exception as e:
        logging.error(f"{description} failed: {e}")
        return None


def clear_leases() -> None:
    """
    Clear DHCP leases to reset device tracking.
    """
    if os.path.exists(DHCP_LEASES_FILE):
        logging.info("Clearing DHCP leases...")
        with open(DHCP_LEASES_FILE, "w") as file:
            file.truncate(0)
        execute_command(
            ["sudo", "systemctl", "restart", "dnsmasq"],
            description="Restarting dnsmasq...",
            success_msg="DHCP leases cleared and dnsmasq restarted.",
            error_msg="Failed to restart dnsmasq after clearing leases"
        )
    else:
        logging.warning(f"{DHCP_LEASES_FILE} does not exist. No leases to clear.")


def set_interface_state(interface: str, state: str) -> None:
    """
    Set the state (up/down) of a network interface.

    :param interface: Name of the network interface.
    :param state: Desired state ("up" or "down").
    """
    execute_command(
        ["sudo", "ifconfig", interface, state],
        description=f"Setting interface {interface} {state}...",
        success_msg=f"{interface} successfully set to {state}.",
        error_msg=f"Failed to set {interface} to {state}"
    )


def disable_wifi() -> None:
    """
    Disable the WiFi interface.
    """
    set_interface_state(WIFI_INTERFACE, "down")


def enable_hotspot() -> None:
    """
    Enable the hotspot services.
    """
    logging.info("Starting hotspot...")
    for service in HOTSPOT_SERVICES:
        execute_command(
            ["sudo", "systemctl", "restart", service],
            description=f"Starting {service}...",
            success_msg=f"{service} started successfully.",
            error_msg=f"Failed to restart {service}"
        )
    logging.info("Hotspot started successfully.")


def disable_hotspot() -> None:
    """
    Disable the hotspot services.
    """
    logging.info("Stopping hotspot...")
    for service in HOTSPOT_SERVICES:
        execute_command(
            ["sudo", "systemctl", "stop", service],
            description=f"Stopping {service}",
            success_msg=f"{service} stopped successfully.",
            error_msg=f"Failed to stop {service}"
        )
    logging.info("Hotspot stopped successfully.")


def check_hotspot_status() -> bool:
    """
    Check if the hotspot is active.

    :return: True if the hotspot is active, False otherwise.
    """
    result = execute_command(
        ["systemctl", "is-active", "hostapd"],
        description="Checking hotspot status",
        success_msg="Hostapd status checked.",
        error_msg="Failed to check hostapd status"
    )
    if result and result.stdout.strip() == "active":
        logging.info("Hotspot is active.")
        return True
    logging.error("Hotspot is not active. Please check the configuration.")
    return False


def check_wifi_mode(interface: str = WIFI_INTERFACE) -> Optional[str]:
    """
    Check the current mode of the WiFi interface.

    :param interface: Name of the network interface to check.
    :return: "AP" if in Access Point mode, "Managed" if in Managed mode, None otherwise.
    """
    logging.info(f"Checking the current mode of {interface}...")
    result = execute_command(
        ["iwconfig", interface],
        description=f"Getting mode of {interface}",
        success_msg=f"Mode of {interface} retrieved successfully.",
        error_msg=f"Failed to retrieve mode of {interface}"
    )
    if result:
        output = result.stdout
        if "Mode:Master" in output:
            logging.info(f"{interface} is in Access Point (AP) mode.")
            return "AP"
        if "Mode:Managed" in output:
            logging.info(f"{interface} is in Managed mode.")
            return "Managed"
        logging.warning(f"Unknown mode for {interface}.")
    return None


def set_wifi_to_ap(interface: str = WIFI_INTERFACE) -> None:
    """
    Set the WiFi interface to Access Point (AP) mode.

    :param interface: Name of the network interface to set to AP mode.
    """
    logging.info(f"Setting {interface} to Access Point (AP) mode...")
    execute_command(
        ["sudo", "ip", "link", "set", interface, "down"],
        description=f"Setting {interface} down...",
        success_msg=f"{interface} set to down.",
        error_msg=f"Failed to set {interface} down."
    )
    execute_command(
        ["sudo", "ip", "link", "set", interface, "up"],
        description=f"Setting {interface} up...",
        success_msg=f"{interface} set to Access Point (AP) mode.",
        error_msg=f"Failed to set {interface} to AP mode."
    )


def monitor_connections(start_robot_callback: callable) -> None:
    """
    Monitor DHCP leases file for new connections and invoke the robot callback.

    :param start_robot_callback: Callback function to invoke when a new device connects.
    """
    logging.info("Monitoring for new device connections...")
    last_device_mac: Optional[str] = None

    while True:
        if os.path.exists(DHCP_LEASES_FILE):
            with open(DHCP_LEASES_FILE, "r") as file:
                lines = file.readlines()
                if lines:
                    first_device = lines[0].split()
                    device_mac, device_name = first_device[1], first_device[3]

                    if device_mac != last_device_mac:
                        logging.info(f"New device connected: {device_name} ({device_mac})")
                        start_robot_callback()
                        last_device_mac = device_mac
                else:
                    if last_device_mac:
                        logging.info(f"Device disconnected: {last_device_mac}")
                        disable_hotspot()
                        last_device_mac = None
        else:
            logging.warning(f"{DHCP_LEASES_FILE} not found. Is dnsmasq running?")
        time.sleep(10)
