from openai import OpenAI
import os
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import requests

load_dotenv()
key = os.getenv('api_key')

client = OpenAI(api_key=key)



response = client.images.generate(
        model="dall-e-3",
        prompt="Image of a dolphin",
        quality="hd",
        n=1,
)
 
img = response.data[0].url
print(img)

response = requests.get(response.data[0].url)
image = Image.open(BytesIO(response.content))
image.show()