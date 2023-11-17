from flask import Flask, request, jsonify, send_file
from google.cloud import vision
from google.cloud import translate
from google.cloud import texttospeech
import io
import os

app = Flask(__name__)

def translate_text(target: str, text: str) -> dict:
    from google.cloud import translate_v2 as translate

    translate_client = translate.Client()
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    result = translate_client.translate(text, target_language=target)
    
    if target == "ko":
        synthesize_text(result["translatedText"], "ko-KR")
    elif target == "en":
        synthesize_text(result["translatedText"], "en-US")
    
    return result

def detect_language(text):
    project_id = "civil-icon-396606"
    client = translate.TranslationServiceClient()
    location = "global"
    parent = f"projects/{project_id}/locations/{location}"

    response = client.detect_language(
        content=text,
        parent=parent,
        mime_type="text/plain",  # mime types: text/plain, text/html
    )

    for language in response.languages:
        if language.language_code == "ko":
            return translate_text("en", text)
        else:
            return translate_text("ko", text)

def synthesize_text(text, target):
    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=target,
        name=target + "-Standard-C",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        request={"input": input_text, "voice": voice, "audio_config": audio_config}
    )
    with open("output.mp3", "wb") as out:
        out.write(response.audio_content)
        print('Audio content written to file "output.mp3"')

@app.route('/api/translate', methods=['POST'])
def process_image():
    # 클라이언트로부터 이미지를 받음
    file = request.files['image']
    image_content = file.read()

    # 이미지에서 텍스트를 추출
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_content)
    response = client.text_detection(image=image)
    image_text = response.text_annotations
    rs_text = ''
    if len(image_text) == 0:
        rs_text = "이미지에 아무런 텍스트가 없습니다."
        synthesize_text(rs_text, "ko-KR")
    else:
        translated_text = detect_language(image_text[0].description.replace("\n", " "))
        print(image_text[0].description.replace("\n", " "), translated_text["translatedText"])
        rs_text = translated_text["translatedText"]
    
    with open('output.mp3', 'rb') as f:
        mp3_data = f.read()
    
    return jsonify({
        'text' : rs_text,
        'mp3' : mp3_data.decode('latin1')
    })
    
    

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)