import ollama
from openai import OpenAI
from pathlib import Path
import os
import base64

prompt = """Du bist Barrierefreiheits-Assistent.
Du erstellst eine deutsche Bildbeschreibung für den Alt-Text.
Beschreibe, was auf dem Bild zu sehen ist.
Beginne sofort mit der Beschreibung. Sei präzise und knapp.
Du erstellst eine deutsche Bildbeschreibung für den Alt-Text.  
Beschreibe, was auf dem Bild zu sehen ist. 
Beginne sofort mit der Beschreibung. Sei präzise und knapp. 
Wenn das Bild lesbaren Text enthält, zitiere diesen Text."""
client = OpenAI(api_key = os.environ.get('OPENAI_API_KEY'))
# Use GPT-4 mini to describe images
OLLAMA = False

def gpt4_description(image_url):
    # Check a local image by converting it to b64: 
    # image_url = f"data:image/jpeg;base64,{b64_image}"
    response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url":  image_url,
                            }
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
    return response.choices[0].message.content

def llama_description(b64_image):
    response = ollama.chat(
        model="llama3.2-vision",
        messages=[{
            'role': 'user',
            'content': prompt,
            'images': [b64_image]
            }]
        )
    return response['message']['content'].strip()


def ai_description(fname):
    # Use llama3.2-vision to describe images
    # Use whisper.cpp command-line tool to transcribe audio and video
    desc = f"Filetype: {fname.lower()[-4:]}"
    image_folder = os.path.join(os.path.dirname(__file__), 'messages')
    file_path = os.path.join(image_folder, fname)
    file_path = os.path.join(image_folder, fname)        
    if fname.lower().endswith(('.jpg', '.jpeg')):
        try:
            with open(file_path, 'rb') as file:
                file_content = file.read()
                image = base64.b64encode(file_content).decode('utf-8')
        except FileNotFoundError:
            return "!!!Datei nicht gefunden!!!"
        except Exception as e:
            raise Exception(f"Error reading file {fname}: {str(e)}")
        if OLLAMA:
            desc2 = llama_description(image)
        else:
            desc2 = gpt4_description(image)
            desc2 = gpt4_description(image) 
        desc = f"{desc}\n{desc2}"
        
    # Return ai-generated description
    return desc
