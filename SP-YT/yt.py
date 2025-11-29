import yt_dlp

def list_formats(video_url):
    ydl_opts = {
        'listformats': True  # Lists all available formats
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(video_url, download=False)


def download_youtube_video(video_url, format_code):
    ydl_opts = {
        'format': format_code  # Use specified format
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])


# Ask for video URL
video_url = input("Please enter the full URL of the YouTube video: ")

# Ask which format to download
format_code = '140'

try:
    print(f"Downloading video in format {format_code}...")
    download_youtube_video(video_url, format_code)
    print("Download completed successfully.")
except Exception as e:
    print(f"An error occurred: {e}")
