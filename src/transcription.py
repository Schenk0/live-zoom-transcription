import os
import wave
import io
from openai import OpenAI  # type: ignore

def handle_audio_transcription(audio_data: bytes, channels: int, sample_width: int, framerate: int) -> str | None:
    """
    Handle near-realtime audio transcription using OpenAI's Whisper API.
    
    Instead of writing to disk, this function writes the buffered PCM data into an in-memory WAV file,
    which reduces the I/O overhead and improves latency.
    
    Args:
        audio_data: Raw PCM audio data.
        channels: Number of audio channels (1 for mono, 2 for stereo).
        sample_width: Number of bytes per sample.
        framerate: Audio sample rate in Hz.
        
    Returns:
        str | None: Transcribed text if successful; None otherwise.
    """
    try:
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(framerate)
            wf.writeframes(audio_data)
        wav_io.seek(0)
        wav_io.name = "audio.wav"
        
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            print("No OPENAI_API_KEY found in environment")
            return None

        client = OpenAI(api_key=api_key)
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=wav_io
        )
        
        return transcription.text

    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return None
