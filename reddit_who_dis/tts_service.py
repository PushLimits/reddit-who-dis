import logging
from typing import Optional
from openai import OpenAI

class TTSService:
    """Service for generating speech audio from text using Kokoro TTS via OpenAI-compatible API."""

    def __init__(self, base_url: str = "http://localhost:8880/v1", default_voice: str = "af_sky+af_bella"):
        """
        Args:
            base_url: Base URL for the local Kokoro TTS server (OpenAI-compatible endpoint).
            default_voice: Default voice to use (e.g., 'kokoro' or a voicepack combo).
        """
        self.client = OpenAI(base_url=base_url, api_key="not-needed")
        self.default_voice = default_voice

    def synthesize_speech(self, text: str, voice: Optional[str] = None, save_path: Optional[str] = None, stream: bool = False):
        """
        Generate speech audio from text, with options to stream (playback), save to file, or return bytes.

        Args:
            text: The text to synthesize.
            voice: Voice name or combo (optional).
            save_path: If provided, save the audio to this file path (WAV for PCM, MP3 for non-PCM).
            stream: If True, stream audio in real time (playback as it streams).

        Returns:
            If stream is False and save_path is not set, returns the audio bytes.
            If save_path is set and audio is saved successfully, returns the save_path.
            Otherwise, returns None.
        """
        import numpy as np
        import sounddevice as sd
        import wave

        voice_name = voice if voice is not None else self.default_voice
        sample_rate = 24000  # Known sample rate for Kokoro PCM
        all_audio_data = bytearray()
        chunk_count = 0
        total_bytes = 0

        # Determine response_format
        response_format = None
        if stream:
            response_format = "pcm"
        elif save_path:
            if save_path.endswith('.wav'):
                response_format = "wav"
            elif save_path.endswith('.mp3'):
                response_format = "mp3"
            elif save_path.endswith('.flac'):
                response_format = "flac"
            elif save_path.endswith('.aac'):
                response_format = "aac"
            elif save_path.endswith('.opus'):
                response_format = "opus"
            else:
                response_format = "mp3"  # Default to mp3 if unknown

        try:
            with self.client.audio.speech.with_streaming_response.create(
                model="kokoro",
                voice=voice_name,
                input=text,
                response_format=response_format,
            ) as response:
                if stream or (save_path and save_path.endswith('.wav')):
                    # PCM streaming for playback and/or WAV saving
                    stream_obj = None
                    if stream:
                        stream_obj = sd.OutputStream(
                            samplerate=sample_rate,
                            channels=1,
                            dtype=np.int16,
                            blocksize=1024,
                            latency="low",
                        )
                        stream_obj.start()
                    for chunk in response.iter_bytes(chunk_size=512):
                        if chunk:
                            chunk_count += 1
                            total_bytes += len(chunk)
                            all_audio_data.extend(chunk)
                            if stream:
                                audio_chunk = np.frombuffer(chunk, dtype=np.int16)
                                stream_obj.write(audio_chunk)
                    if stream:
                        stream_obj.stop()
                        stream_obj.close()
                    if save_path and save_path.endswith('.wav'):
                        with wave.open(save_path, "wb") as wav_file:
                            wav_file.setnchannels(1)
                            wav_file.setsampwidth(2)
                            wav_file.setframerate(sample_rate)
                            wav_file.writeframes(all_audio_data)
                        return save_path
                    if not stream and not save_path:
                        return bytes(all_audio_data)
                else:
                    # Non-PCM (e.g., MP3, FLAC, etc.) - just save or return
                    if save_path:
                        response.stream_to_file(save_path)
                        return save_path
                    else:
                        return b"".join(response.iter_bytes())
        except Exception as e:
            logging.error(f"TTS synthesis failed: {e}")
            return None