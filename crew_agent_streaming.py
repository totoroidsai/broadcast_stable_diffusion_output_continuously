import os
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from crewai import Agent, Task, Crew

# ---------------------------
# CONFIGURATION
# ---------------------------
WATCH_FOLDER = "streamer_1/raw"
MIN_VIDEOS = 3  # Number of videos required to trigger streaming
STREAM_URL = "rtmp://localhost:1935/live"  # Change port if needed

# ---------------------------
# AGENT 1: Folder Monitor Agent
# ---------------------------
class FolderMonitor(FileSystemEventHandler):
    def __init__(self, task_agent):
        self.task_agent = task_agent

    def on_modified(self, event):
        """Triggered when a file is created or modified in the folder."""
        if event.is_directory:
            return
        time.sleep(2)  # Short delay to ensure file is fully written
        self.task_agent.run()

def count_videos():
    """Counts video files in the folder."""
    return [f for f in os.listdir(WATCH_FOLDER) if f.endswith(('.mp4', '.mkv', '.mov'))]

def get_video_list():
    """Generates FFmpeg-compatible input file list."""
    video_files = count_videos()
    list_file_path = os.path.join(WATCH_FOLDER, "file_list.txt")
    
    with open(list_file_path, "w") as f:
        for video in video_files:
            f.write(f"file '{os.path.join(WATCH_FOLDER, video)}'\n")

    return list_file_path, len(video_files)

monitor_agent = Agent(
    role="Folder Monitor",
    goal="Monitor the folder for new video files and trigger the streaming process once at least X videos are available.",
    backstory="You are responsible for ensuring the required number of videos are available before streaming starts.",
    allow_delegation=False
)

def monitor_folder():
    video_count = len(count_videos())
    if video_count >= MIN_VIDEOS:
        print(f"[V] Found {video_count} videos. Triggering FFmpeg streaming.")
        return "START_STREAMING"
    else:
        print(f"[W] Waiting for more videos... (Current: {video_count}/{MIN_VIDEOS})")
        return "WAIT"

monitor_task = Task(
    description="Check if the required number of videos exist. If they do, trigger the FFmpeg streaming process.",
    agent=monitor_agent,
    function=monitor_folder
)

# ---------------------------
# AGENT 2: FFmpeg Stream Agent
# ---------------------------
stream_agent = Agent(
    role="Streaming Manager",
    goal="Combine and stream the videos in real-time using FFmpeg.",
    backstory="You are responsible for managing the FFmpeg streaming process, ensuring smooth and continuous video playback.",
    allow_delegation=False
)

def stream_videos():
    """Streams combined videos without saving them."""
    list_file, video_count = get_video_list()

    if video_count < MIN_VIDEOS:
        return "[X] Not enough videos to start streaming."

    print("[OO...OOO] Starting FFmpeg Streaming...")

    ffmpeg_cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-b:v", "3000k",
        "-maxrate", "3000k",
        "-bufsize", "6000k",
        "-f", "flv", STREAM_URL
    ]

    subprocess.run(ffmpeg_cmd)
    
    print("[X] Streaming ended. Restarting from the first video.")
    return "RESTART_MONITOR"

stream_task = Task(
    description="Combine all videos and stream them to the localhost endpoint without saving.",
    agent=stream_agent,
    function=stream_videos
)

# ---------------------------
# CREW SETUP & MONITORING
# ---------------------------
crew = Crew(agents=[monitor_agent, stream_agent], tasks=[monitor_task, stream_task])

def start_monitoring():
    """Monitors the folder continuously for new videos."""
    print(f"[O] Watching folder: {WATCH_FOLDER}")

    observer = Observer()
    observer.schedule(FolderMonitor(crew), WATCH_FOLDER, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_monitoring()
