from fastapi import FastAPI, UploadFile
from fastapi.responses import StreamingResponse

from dotenv import load_dotenv

from openai import OpenAI
import os
import json
import requests

# take environment variables from .env.
load_dotenv()


client = OpenAI(api_key=os.environ.get("OPEN_AI_KEY"),
                organization=os.environ.get("OPEN_AI_ORG"))
elevenlabs_key = os.getenv("ELEVENLABS_KEY")


app = FastAPI()


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.post("/talk")
async def post_audio(file: UploadFile):
    user_message = transcribe_audio(file)
    chat_response = get_chat_response(user_message)
    audio_output = text_to_speech(chat_response)

    def iterfile():
        yield audio_output

    return StreamingResponse(iterfile(), media_type="audio/mpeg")


# Functions
def transcribe_audio(file):
    audio_file = open(file.filename, "rb")
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    return transcript.text


def get_chat_response(user_message):
    messages = load_messages()
    # print('user msg', user_message)
    messages.append({"role": "user", "content": user_message})

    # Send to OpenAI
    gpt_response = {"role": "assistant",
                    "content": "The Los Angeles Dodgers won the World Series in 2020."},
    gpt_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    parsed_gpt_response = gpt_response.choices[0].message.content

    # Save messages
    save_messages(user_message, parsed_gpt_response)

    return parsed_gpt_response


def load_messages():
    messages = []
    file = 'database.json'

    # IF FILE IS empty we need to add the context
    empty = os.stat(file).st_size == 0

    # IF FILE IS NOT empty loop through history and add to messages
    if not empty:
        with open(file) as db_file:
            data = json.load(db_file)
            for item in data:
                messages.append(item)
    else:
        messages.append(
            {"role": "system", "content": "You are interviewing the user for a front-end React developer position. Ask short questions that are relevant to a junior level developer. Your name is Greg. The user is Daniel. Keep responses under 30 words and be funny sometimes."})

    return messages


def save_messages(user_message, gpt_response):
    file = 'database.json'
    messages = load_messages()
    messages.append({"role": "user",
                     "content": user_message})
    messages.append({"role": "assistant",
                     "content": gpt_response})
    with open(file, 'w') as f:
        json.dump(messages, f)


def text_to_speech(text):
    voice_id = "TX3LPaxmHKxFdv7VOQHJ"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    payload = {
        "model_id": "eleven_monolingual_v1",
        "text": text,
        "voice_settings": {
            "similarity_boost": 0,
            "stability": 0,
            "style": 0.5,
            "use_speaker_boost": True
        }
    }
    headers = {"Content-Type": "application/json",
               "accept": "audio/mpeg",
               "xi-api-key": elevenlabs_key}

    try:
        response = requests.request("POST", url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            print('Something went wrong')
    except Exception as e:
        print(e)
