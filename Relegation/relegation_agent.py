import os
import time
import psutil
import socket
from crewai import Agent, Task, Crew

# ---------------------------
# CONFIGURATION
# ---------------------------
PORT_RANGE = (1935, 1950)  # Range of ports to monitor (adjust as needed)
CHECK_INTERVAL = 5  # Time (seconds) between checks
RELEGATE_INTERVAL = 60  # Time (seconds) before renaming the folder
TARGET_FOLDER = "streamer_1"  # Folder to rename

# ---------------------------
# HELPER FUNCTIONS
# ---------------------------
viewer_counts = {}  # Stores viewers per port

def get_active_ports():
    """Scans for active listening ports within the range."""
    active_ports = []
    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr.port in range(*PORT_RANGE) and conn.status == 'LISTEN':
            active_ports.append(conn.laddr.port)
    return active_ports

def get_viewer_count(port):
    """Estimates viewer count by checking active connections on a port."""
    count = 0
    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr.port == port and conn.status == 'ESTABLISHED':
            count += 1
    return count

def update_viewer_counts():
    """Updates viewer count for each active streaming port."""
    global viewer_counts
    active_ports = get_active_ports()
    
    for port in active_ports:
        viewer_counts[port] = get_viewer_count(port)
    
    print(f"[!!!] Current Viewers per Port: {viewer_counts}")

# ---------------------------
# AGENT 1: Port Monitor Agent
# ---------------------------
port_monitor_agent = Agent(
    role="Port Monitor",
    goal="Monitor active streaming ports and track viewer counts.",
    backstory="You are responsible for keeping an accurate count of viewers watching streams on each port.",
    allow_delegation=False
)

def monitor_ports():
    """Continuously updates viewer counts."""
    while True:
        update_viewer_counts()
        time.sleep(CHECK_INTERVAL)

port_monitor_task = Task(
    description="Monitor streaming ports and track viewer counts.",
    agent=port_monitor_agent,
    function=monitor_ports
)

# ---------------------------
# AGENT 2: Folder Relegation Agent
# ---------------------------
folder_relegation_agent = Agent(
    role="Folder Manager",
    goal="Rename the target folder after a set period.",
    backstory="You ensure that the folder is renamed when the time limit is reached.",
    allow_delegation=False
)

def relegate_folder():
    """Renames the folder after X seconds."""
    time.sleep(RELEGATE_INTERVAL)

    new_folder_name = f"{TARGET_FOLDER}_relegated"
    
    if os.path.exists(TARGET_FOLDER):
        os.rename(TARGET_FOLDER, new_folder_name)
        print(f"[O] Renamed '{TARGET_FOLDER}' to '{new_folder_name}'")
    else:
        print(f"[!] Target folder '{TARGET_FOLDER}' does not exist.")

folder_relegation_task = Task(
    description="Rename the folder after X seconds.",
    agent=folder_relegation_agent,
    function=relegate_folder
)

# ---------------------------
# CREW SETUP
# ---------------------------
crew = Crew(agents=[port_monitor_agent, folder_relegation_agent], tasks=[port_monitor_task, folder_relegation_task])

if __name__ == "__main__":
    crew.kickoff()
