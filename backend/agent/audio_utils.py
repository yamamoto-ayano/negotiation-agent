import os
import tempfile
import subprocess
from typing import List


def split_audio(audio_path: str, chunk_length_sec: int = 300) -> List[str]:
    """
    指定した音声ファイルをchunk_length_secごとに分割し、一時ファイルとして保存。
    分割ファイルのパスリストを返す。
    """
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    temp_dir = tempfile.mkdtemp(prefix="audio_chunks_")
    output_pattern = os.path.join(temp_dir, f"{base_name}_chunk_%03d.wav")

    # ffmpegで分割
    cmd = [
        "ffmpeg",
        "-i", audio_path,
        "-f", "segment",
        "-segment_time", str(chunk_length_sec),
        "-c", "copy",
        output_pattern
    ]
    subprocess.run(cmd, check=True)

    # 分割されたファイルのパスを取得
    chunk_paths = sorted([
        os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
        if f.startswith(base_name + "_chunk_") and f.endswith(".wav")
    ])
    return chunk_paths 