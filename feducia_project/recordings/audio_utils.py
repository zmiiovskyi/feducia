import os
import subprocess


def extract_audio_from_video(video_path):
    base_name, _ = os.path.splitext(video_path)
    audio_path = f"{base_name}.wav"

    command = [
        "ffmpeg",
        "-y",
        # без мережі та плейлистів (HLS, concat), які можуть читати чужі файли
        "-protocol_whitelist", "file",
        "-format_whitelist", "mov,matroska",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path,
    ]

    subprocess.run(
        command,
        check=True,
        timeout=300,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return audio_path