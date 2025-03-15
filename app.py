from flask import Flask, jsonify
from speech_recog import record_audio, encrypt_audio, transcribe_with_assemblyai, transcribe_with_google, list_audio_devices
import os

app = Flask(__name__)

@app.route('/recognize', methods=['GET'])
def recognize_speech():
    """Records user's voice, processes it, and returns transcription."""
    output_path = "E:/Sir Alexander/Sir Alexander/speech/temp_audio.wav"

    try:
        # List available audio devices and select one
        valid_device = list_audio_devices()

        # Record audio
        print("Recording... Speak now!")
        record_audio(output_path, input_device_index=valid_device)

        # Encrypt the recorded audio
        encrypted_path = encrypt_audio(output_path)

        # Transcribe using AssemblyAI
        print("Transcribing with AssemblyAI...")
        transcription = transcribe_with_assemblyai(output_path)

        # Fallback to Google STT if AssemblyAI fails
        if "Error" in transcription or not transcription.strip():
            print("AssemblyAI failed. Trying Google Speech-to-Text...")
            transcription = transcribe_with_google(output_path)

        # Clean up temporary files
        os.remove(output_path)
        os.remove(encrypted_path)

        return jsonify({'transcription': transcription})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # Get PORT from Render, default 10000
    app.run(host='0.0.0.0', port=port, debug=True)
