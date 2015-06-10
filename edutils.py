import psutil

def is_ed_running():
    for p in psutil.process_iter():
        if p.name().lower().startswith("elitedangerous"):
            return True

    # WBB REMOVE WHEN FULL TEST AND SHIP
    # return False
    return True
