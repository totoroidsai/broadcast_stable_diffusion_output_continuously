import os
import subprocess
import time
from crewai import Agent, Task, Crew

# ---------------------------
# CONFIGURATION
# ---------------------------
VIDEO_FOLDER = "streamer_1/raw"
STREAM_URL = "rtmp://localhost:1935/live"  # Change if needed
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.mov')  # Supported formats
BATCH_SIZE = 5  # Number of videos per batch
DELETE_COUNT = 2  # Number of oldest files to delete after a full loop

# ---------------------------
# HELPER FUNCTIONS
# ---------------------------
def get_video_list():
    """Returns a sorted list of video file paths."""
    videos = sorted([
        os.path.join(VIDEO_FOLDER, f) for f in os.listdir(VIDEO_FOLDER)
        if f.endswith(VIDEO_EXTENSIONS)
    ])
    
    if not videos:
        print("[X] No videos found in the folder.")
    
    return videos

def get_batches(video_list, batch_size):
    """Splits the video list into batches."""
    return [video_list[i:i + batch_size] for i in range(0, len(video_list), batch_size)]

# ---------------------------
# AGENT 1: Streaming Manager
# ---------------------------
stream_agent = Agent(
    role="Streaming Manager",
    goal="Stream videos in batches, looping after all videos are streamed.",
    backstory="You manage FFmpeg streaming, ensuring it runs in batches and loops continuously.",
    allow_delegation=False
)

def stream_videos():
    """Streams videos in batches and loops after completion."""
    while True:
        videos = get_video_list()
        if not videos:
            print("[0] No videos found. Retrying in 30 seconds...")
            time.sleep(30)
            continue
        
        batches = get_batches(videos, BATCH_SIZE)

        for batch in batches:
            print(f"[!] Now Streaming Batch: {batch}")

            # Create temporary file list for FFmpeg
            list_file_path = os.path.join(VIDEO_FOLDER, "file_list.txt")
            with open(list_file_path, "w") as f:
                for video in batch:
                    f.write(f"file '{video}'\n")

            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file_path,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-tune", "zerolatency",
                "-b:v", "3000k",
                "-maxrate", "3000k",
                "-bufsize", "6000k",
                "-f", "flv", STREAM_URL
            ]
            
            subprocess.run(ffmpeg_cmd)

        print("[O] Restarting from the first video...")
        delete_oldest_videos()  # Trigger cleanup after full loop

stream_task = Task(
    description="Stream all videos in batches and loop after completion.",
    agent=stream_agent,
    function=stream_videos
)

# ---------------------------
# AGENT 2: File Cleanup Agent
# ---------------------------
cleanup_agent = Agent(
    role="File Cleanup Manager",
    goal="Delete the oldest X number of files after a full streaming loop.",
    backstory="You manage storage by removing the oldest videos to prevent excessive buildup.",
    allow_delegation=False
)

def delete_oldest_videos():
    """Deletes the oldest X number of files after a full loop."""
    videos = get_video_list()
    
    if len(videos) > DELETE_COUNT:
        oldest_files = videos[:DELETE_COUNT]
        for file in oldest_files:
            try:
                os.remove(file)
                print(f"[🗑️] Deleted: {file}")
            except Exception as e:
                print(f"[X] Error deleting {file}: {e}")
    else:
        print("[!] Not enough videos to delete.")

cleanup_task = Task(
    description="Delete the oldest videos after each full loop.",
    agent=cleanup_agent,
    function=delete_oldest_videos
)

# ---------------------------
# CREW SETUP
# ---------------------------
crew = Crew(agents=[stream_agent, cleanup_agent], tasks=[stream_task, cleanup_task])

if __name__ == "__main__":
    crew.kickoff()
