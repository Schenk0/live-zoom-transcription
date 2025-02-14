import os
import wave
import tempfile
from openai import OpenAI # type: ignore

def handle_audio_transcription(audio_data: bytes, channels: int, sample_width: int, framerate: int) -> str | None:
    """
    Handle audio transcription using OpenAI's Whisper API
    
    Args:
        audio_data: Raw PCM audio data
        channels: Number of audio channels (1 for mono, 2 for stereo)
        sample_width: Number of bytes per sample
        framerate: Audio sample rate in Hz
        
    Returns:
        str | None: Transcribed text if successful, None if failed
    """
    try:
        # Write the buffered PCM data to a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_filename = tmp_file.name
            with wave.open(tmp_file, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(sample_width)
                wf.setframerate(framerate)
                wf.writeframes(audio_data)

        # Send to Whisper API
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            print("No OPENAI_API_KEY found in environment")
            return None

        client = OpenAI(api_key=api_key)
        with open(tmp_filename, 'rb') as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            
        # Clean up temporary file
        os.remove(tmp_filename)
        
        transcribed_text = transcription.text
        return transcribed_text

    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return None
