import re
import sys
import os
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

# Helper function to parse the YouTube video ID from a URL.
def parse_video_id(url: str) -> str:
    match = re.search(r'(?:v=|/)([0-9A-Za-z_-]{11})', url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Unable to find a valid video ID in the given URL.")

# Use yt-dlp to retrieve the title and uploader.
def get_title_and_uploader(url: str):
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get('title', 'Unknown_Title')
        uploader = info.get('uploader', 'Unknown_Uploader')
        return title, uploader

# Fetch transcript, distinguishing between manual and auto-generated.
def fetch_transcripts(video_id: str, language: str = 'en'):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        manual_transcript, auto_transcript = "", ""
        
        if language in transcript_list._manually_created_transcripts:
            manual_transcript = "\n".join([item['text'] for item in transcript_list.find_manually_created_transcript([language]).fetch()])
        if language in transcript_list._generated_transcripts:
            auto_transcript = "\n".join([item['text'] for item in transcript_list.find_generated_transcript([language]).fetch()])
        
        return manual_transcript, auto_transcript
    except Exception as e:
        print(f"Could not retrieve transcripts for video ID {video_id}. Error: {e}")
        return "", ""

def save_transcripts(url: str) -> None:
    video_id = parse_video_id(url)
    title, uploader = get_title_and_uploader(url)
    manual_transcript, auto_transcript = fetch_transcripts(video_id)
    safe_title = re.sub(r'[^A-Za-z0-9_-]+', '_', title)
    
    current_directory = os.getcwd()
    
    if manual_transcript:
        filename_manual = os.path.join(current_directory, f"{safe_title}_manual.txt")
        with open(filename_manual, 'w', encoding='utf-8') as f:
            f.write(f"Podcast Episode: {title}\n")
            f.write(f"Uploader: {uploader}\n\n")
            f.write(manual_transcript)
        print(f"Manual transcript saved as: {filename_manual}")
    
    if auto_transcript:
        filename_auto = os.path.join(current_directory, f"{safe_title}_auto.txt")
        with open(filename_auto, 'w', encoding='utf-8') as f:
            f.write(f"Podcast Episode: {title}\n")
            f.write(f"Uploader: {uploader}\n\n")
            f.write(auto_transcript)
        print(f"Auto-generated transcript saved as: {filename_auto}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python transcript_extractor.py <youtube_url>")
        sys.exit(1)
    youtube_url = sys.argv[1]
    save_transcripts(youtube_url)

if __name__ == "__main__":
    main()
