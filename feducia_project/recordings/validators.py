from django.core.exceptions import ValidationError

VIDEO_EXTENSIONS = ("mp4", "m4v", "mov", "webm", "mkv")
MAX_VIDEO_SIZE = 500 * 1024 * 1024

EBML_SIGNATURE = b"\x1a\x45\xdf\xa3"
MP4_BOXES = (b"ftyp", b"moov", b"mdat", b"wide")


def validate_video(video_file):
    """Перевіряє розмір, розширення та сигнатуру файлу, повертає розширення."""
    extension = video_file.name.rsplit(".", 1)[-1].lower()

    if extension not in VIDEO_EXTENSIONS:
        raise ValidationError("Supported formats: MP4, M4V, MOV, WebM, MKV.")

    if video_file.size > MAX_VIDEO_SIZE:
        raise ValidationError("The video must be smaller than 500 MB.")

    header = video_file.read(12)
    video_file.seek(0)

    # ffmpeg визначає формат за вмістом, тому розширення недостатньо
    if not (header.startswith(EBML_SIGNATURE) or header[4:8] in MP4_BOXES):
        raise ValidationError("The file is not a valid video.")

    return extension
