import whisper
from datetime import datetime, timedelta
import subprocess
import locale
import serial

from flask import (Flask, redirect, render_template, request,
                   send_from_directory, url_for, jsonify, Response, abort)

import azure.cognitiveservices.speech as speechsdk
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas

model = whisper.load_model("base")

database = list([
    {
        "documentId": "39178931851",
        "balance" : 99560.10,
        "emergencyBalance": 0,
        "displayBalance": 0,
        "emergencyMode": False,
        "emergencyContact": "11997090403",
        "indicidentAudio": "",
    }
])

emergencyWords = ["calma", "colaborar", "mato", "tiro", "perdeu", "pedeu", "preiboi", "playboy"]

speech_key, service_region = "6a99be2601ee48129ae96c83d20eab60", "eastus"

account_name = "armazenamentoequipe8"
account_key = "+Majaj4LeBbyZ5GnbgwkWV8ogvVuIaVMAu2qBNJGMEalD0FEdWjnvF/Zw8MsVdP8bdWfjLF208ac+ASt9jmM5w==";
container_name = "containerdeaudios"

blob_service_client = BlobServiceClient.from_connection_string(conn_str="DefaultEndpointsProtocol=https;AccountName=armazenamentoequipe8;AccountKey=+Majaj4LeBbyZ5GnbgwkWV8ogvVuIaVMAu2qBNJGMEalD0FEdWjnvF/Zw8MsVdP8bdWfjLF208ac+ASt9jmM5w==;EndpointSuffix=core.windows.net")

locale.setlocale( locale.LC_ALL, 'pt_BR.ISO8859-1')

ser = serial.Serial('/dev/cu.usbserial-1130')

app = Flask(__name__)

@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

@app.route("/callcenter/incidents", methods=['GET'])
def list_incidents():
    incidents = list(filter(lambda u: u["emergencyMode"] == True, database))
    return jsonify(incidents)

@app.route("/recover/{document_id}", methods=['GET'])
def recover(document_id):
    user = next(filter(lambda u: u["documentId"] == document_id, database), None)

    if not user is None:
        user["emergencyMode"] = False
        user["indicidentAudio"] = ""
        return Response("usuario normalizado", 200)
    else:
        abort(404)
        return abort(Response("usuario nao encontrado"))

@app.route("/balance/{document_id}", methods=['GET'])
def balance(document_id):
    print(document_id)

    user = next(filter(lambda u: u["documentId"] == document_id, database), None)

    if not user is None:
        return jsonify({
            "balance":  locale.currency(user["emergencyBalance"] if user["emergencyMode"] else user["balance"], symbol=None)
        })
    else:
        abort(404)
        return abort(jsonify({
            "message": "usuário não encontrado"
        }))


@app.route("/do-login", methods=['POST'])
async def upload():

    document_id = request.form["documentId"]

    user = next(filter(lambda u : u["documentId"] == document_id, database))

    file_path = f"audios/audio_{datetime.now().isoformat()}.webm"

    with open(file_path, mode="wb") as audio_file:
        audio_file.write(request.files.value[0].data)
        audio_file.close()

    stt = speech_to_text2(file_path).lower()

    print(stt)

    if any(word in stt for word in emergencyWords):
        if not user["emergencyMode"]:
            blob_name = file_path + ".wav"
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

            with open(file=file_path + ".wav", mode="rb") as data:
                blob_client.upload_blob(data)

            token = generate_blob_sas(
                                        account_name=account_name,
                                        account_key=account_key,
                                        container_name=container_name,
                                        blob_name=blob_name,
                                        permission=BlobSasPermissions(read=True),
                                        expiry=datetime.utcnow() + timedelta(days=7))

            url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}"
            user["emergencyBalance"] = 150.00
            user["indicidentAudio"] = f"{url}?{token}"
            ser.write(bytes([255]))

        user["emergencyMode"] = True;

    return jsonify({
        "documentId": user["documentId"]
    })


def convert_and_split(file_path):
    command = ['ffmpeg', '-i', file_path, '-c:a', 'pcm_f32le', file_path + ".wav"]
    subprocess.run(command, stdout=subprocess.PIPE,stdin=subprocess.PIPE)


def speech_to_text2(file_path):
    convert_and_split(file_path)

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    audio_config = speechsdk.audio.AudioConfig(filename=file_path + ".wav")

    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, language="pt-BR", audio_config=audio_config)

    result = speech_recognizer.recognize_once()

    # Check the result
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print("Recognized: {}".format(result.text))
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized: {}".format(result.no_match_details))
        return ""
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print("Speech Recognition canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
        return ""


def speech_to_text(file_path):
    audio = whisper.load_audio(file_path)
    audio = whisper.pad_or_trim(audio)

    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    options = whisper.DecodingOptions(language="pt", fp16=False)
    result = whisper.decode(model, mel, options)
    return result.text


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    app.run()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
