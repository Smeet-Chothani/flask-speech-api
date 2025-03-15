import os
import time
import wave
import pyaudio
import webrtcvad
import assemblyai as aai
import speech_recognition as sr
from cryptography.fernet import Fernet
from pydub import AudioSegment

# Ensure ffmpeg is correctly linked (update paths if needed)
AudioSegment.converter = r"C:\ffmpeg-7.1-full_build\bin\ffmpeg.exe"
AudioSegment.ffprobe = r"C:\ffmpeg-7.1-full_build\bin\ffprobe.exe"

# AssemblyAI API Key (Replace with your actual key)
ASSEMBLYAI_API_KEY = "d5a05d4271894a61ace9741605c8a7e8"

# Generate or load encryption key (store securely!)
encryption_key = Fernet.generate_key()
cipher_suite = Fernet(encryption_key)

# Function to list available audio devices
def list_audio_devices():
    audio = pyaudio.PyAudio()
    print("Available audio devices:")
    valid_devices = []
    
    for i in range(audio.get_device_count()):
        device_info = audio.get_device_info_by_index(i)
        print(f"Index {i}: {device_info['name']} (Input Channels: {device_info['maxInputChannels']})")
        if device_info['maxInputChannels'] > 0:
            valid_devices.append(i)
    
    audio.terminate()
    
    if not valid_devices:
        raise ValueError("No valid audio input devices found. Please connect a microphone.")
    
    return valid_devices[0]  # Return first valid input device


def record_audio(output_path, input_device_index=None):
    vad = webrtcvad.Vad()
    vad.set_mode(3)  # Level 3 = Aggressive (better silence detection)

    audio = pyaudio.PyAudio()
    frame_length = 320  # 20ms frame at 16kHz (160 samples * 2 bytes)

    stream = audio.open(format=pyaudio.paInt16, channels=1, rate=16000,
                        input=True, input_device_index=input_device_index,
                        frames_per_buffer=frame_length)  # 20ms frame size

    print("Recording... Speak now.")

    frames = []
    silence_count = 0
    max_silence = 20  # Stop after detecting 20 consecutive silence frames

    while True:
        try:
            data = stream.read(frame_length, exception_on_overflow=False)
        except IOError as e:
            print(f"Audio buffer error: {e}")
            continue  # Skip to the next iteration

        frames.append(data)

        is_silent = not vad.is_speech(data, 16000)
        silence_count = silence_count + 1 if is_silent else 0

        if silence_count > max_silence:
            print("Silence detected. Stopping recording.")
            break

    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Save recording
    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(16000)
        wf.writeframes(b''.join(frames))

    print("Recording finished.")


# Function to encrypt audio file before uploading
def encrypt_audio(file_path):
    with open(file_path, "rb") as file:
        encrypted_data = cipher_suite.encrypt(file.read())
    
    encrypted_file_path = file_path + ".enc"
    with open(encrypted_file_path, "wb") as file:
        file.write(encrypted_data)

    print("Audio encrypted successfully.")
    return encrypted_file_path

# Function to transcribe using AssemblyAI (Streaming)
def transcribe_with_assemblyai(audio_file_path, retries=3):
    aai.settings.api_key = ASSEMBLYAI_API_KEY  # Set API key once

    for attempt in range(retries):
        try:
            transcriber = aai.Transcriber()  # No need to pass API key here
            transcript = transcriber.transcribe(audio_file_path)  # No 'stream=True'
            return transcript.text  # Use 'text' instead of ['text']
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2)
    return "AssemblyAI failed after multiple attempts."


# Fallback to Google STT
def transcribe_with_google(audio_file_path):
    recognizer = sr.Recognizer()
    
    with sr.AudioFile(audio_file_path) as source:
        print("Listening...")
        audio_data = recognizer.record(source)

    try:
        return recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        return "Sorry, could not understand the audio."
    except sr.RequestError:
        return "Speech recognition service unavailable."
    except Exception as e:
        return f"Google STT Error: {e}"

# Main function
def main():
    output_path = "temp_audio.wav"

    # List available audio devices and select one
    valid_device = list_audio_devices()

    # Record Audio (Stops automatically when silence is detected)
    record_audio(output_path, input_device_index=valid_device)

    # Encrypt the recorded audio before uploading
    encrypted_path = encrypt_audio(output_path)

    # Transcribe Audio using AssemblyAI (Streaming)
    print("\nTranscribing with AssemblyAI... Please wait.")
    result = transcribe_with_assemblyai(output_path)

    # Fallback to Google STT if AssemblyAI fails
    if "Error" in result or not result.strip():
        print("\nAssemblyAI failed. Trying Google Speech-to-Text...")
        result = transcribe_with_google(output_path)

    print("\nTranscribed Text:\n", result)

    # Clean up temporary files
    try:
        os.remove(output_path)
        os.remove(encrypted_path)
    except Exception as e:
        print(f"Error deleting temp file: {e}")

if __name__ == "__main__":
    main()
