from core.hotspot_manager import (
    check_hotspot_status,
    clear_leases,
    disable_wifi,
    set_wifi_to_ap,
    enable_hotspot,
    disable_hotspot,
    check_wifi_mode,
)

def hotspot_routine():
    # Step 1: Clear existing DHCP leases
    clear_leases()

    # Step 2: Disable the WiFi interface
    disable_wifi()

    # Step 3: Check WiFi mode and set to AP mode if necessary
    wifi_mode = check_wifi_mode()
    if wifi_mode != "AP":
        set_wifi_to_ap()

    # Step 4: Enable the hotspot
    enable_hotspot()

    # Step 5: Check if the hotspot is active
    if not check_hotspot_status():
        disable_hotspot()
        return -1
    
    return 1

