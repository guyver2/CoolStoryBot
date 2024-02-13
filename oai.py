from openai import OpenAI
import urllib.request
import logging
from pathlib import Path
import shortuuid
import requests
import shutil
import os
import io
import json
from dotenv import load_dotenv

load_dotenv()

OPENAI_TOKEN: str = os.getenv('OPENAI_TOKEN', '')
FAKE = False
WITH_AUDIO = True


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

client = OpenAI(api_key=OPENAI_TOKEN)

class Audio:
  def __init__(self, story_id: str, text: str):
    self.story_id = story_id
    self.text = text
  
  def generate(self):
    logging.info(f"Generating Audio for story {self.story_id}.")
    if FAKE:
      shutil.copy2("./stories/fake/audio.mp3", f'stories/{self.story_id}/audio.mp3')
      return
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f'Bearer {OPENAI_TOKEN}', 
    }
    data = {
        "model": "tts-1-hd",
        "input": self.text,
        "voice": "nova",
        "response_format": "mp3",
    }
    with requests.post(url, headers=headers, json=data, stream=True) as response:
        if response.status_code == 200:
            buffer = io.BytesIO()
            for chunk in response.iter_content(chunk_size=4096):
                buffer.write(chunk)
            with open( f'stories/{self.story_id}/audio.mp3', "wb") as fd:
              fd.write(buffer.getbuffer())
    

class Cover:
  def __init__(self, story_id: str, prompt:str=''):
    self.story_id = story_id
    self.prompt = prompt + "\nthe image is suitable for children. The image is the cover artwork itself, not the represenstation of a book."
  
  def generate(self):
    logging.info(f"Generating Cover for story {self.story_id}.")
    if FAKE:
      shutil.copy2("./stories/fake/cover.png", f'stories/{self.story_id}/cover.png')
      return
    try:
      response = client.images.generate(
        model="dall-e-3",
        prompt=self.prompt,
        n=1,
        size="1024x1024"
      )
      if response:
        urllib.request.urlretrieve(response.data[0].url, f'stories/{self.story_id}/cover.png')
    except Exception as e:
      logging.error(f'Error while downloading image. {e}')


class Story:
  def __init__(self, plot: str=''):
    self.plot = plot
    self.title = ''
    self.text = ''
    self.cover : Cover|None = None
    self.audio : Audio|None = None
    self.story_id: str = shortuuid.uuid()[0:8]
    self.ready = False

  
  def generate(self):
    logging.info(f"Generating story {self.story_id}, based on: {self.plot}.")
    Path(f'./stories/{self.story_id}').mkdir(parents=True, exist_ok=True)
    if FAKE:
      shutil.copy2("./stories/fake/story.txt", f'stories/{self.story_id}/story.txt')
      with open(f'stories/{self.story_id}/story.txt', "r") as fd:
        self.text = fd.read()
      self.title ="Fake Story"
      self.cover = Cover(self.story_id, "FAKE prompt")
      self.cover.generate()
      if WITH_AUDIO:
          self.audio = Audio(self.story_id, self.text)
          self.audio.generate()
      self.ready = True
      return
    response = client.chat.completions.create(
      model="gpt-4",
      messages=[
        {
          "role": "system",
          #"content": "You are an expert and world renowned author of stories for children. \nYou will be given a short plot and your task is to create a story for kids based on this plot. Your story should be engaging and compelling.  The story should be around a dozen paragraphs long and should properly end.\n\nYour answer should be divided in two sections, one for the text of the story and one for a description of the content and style for the cover image of this story. \nThe story must be written in the same language as the language used for the plot.\nThe cover description must be written in english.\n\nPlease use the following format for your answer:\n\n[STORY]\nHere goes the text of the story...\n\n[COVER]\nHere goes the description of the cover in english..."
                "content": "You are an expert and world renowned author of stories for children. \nYou will be given a short plot and your task is to create a story for kids based on this plot. Your story should be engaging and compelling.  The story should be around a dozen paragraphs long and should properly end.\n\nYour answer should be divided in three sections:\n- The title of the story\n- The text of the story, split as an array of paragraph.\n- A graphical description of the content and style for the cover image of this story. \n\nThe title and the story must be written in the same language as the language used for the plot.\nThe cover description must be written in English.\n\nIt is very important to use the following JSON format for your answer:\n\n{\n\"title\": \"Here goes the title of the story\",\n\"story\": [\n\"Here goes the text of the first paragraph...\",\n\"Here goes the text of the second paragraph...\",\n...\n],\n\"cover\": \"Here goes the description of the cover...\"\n}\n"
        },
        {
          "role": "user",
          "content": self.plot
        }
      ],
      temperature=1,
      max_tokens=2000,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0
    )
    try:
      result = response.choices[0].message.content
      if result:
        data = json.loads(result)
        self.title = data['title']
        self.text = "\n\n".join(data['story'])
        cover = data['cover']
        self.cover = Cover(self.story_id, cover)
        with open(f'./stories/{self.story_id}/story.txt', "w") as fd:
          fd.write(self.text)
        self.cover.generate()

        if WITH_AUDIO:
          self.audio = Audio(self.story_id, self.text)
          self.audio.generate()

        self.ready = True
        logging.info('Done')
      else:
        raise ValueError("Empty OpenAI API response")
    except Exception as e:
      logging.error(f"Error while generating a story with plot: {self.plot}\n\n{e}")





if __name__ == "__main__":
  # s = Story("Une petite sirene de 6 ans qui s'appelle Jeanne aimerai avoir une licorne pour amie.")
  # s = Story("Deux petites filles, Jeanne et Zoé, premières femmes astronautes à poser le pied sur une planète inconnue. Elles reviennent finalement chez elles en héroïnes")
  # s = Story("un chat et d'une souris qui deviennent amies et qui finissent par partager un gros gateau")
  # s = Story("Un lapin n'aime pas les carrotes")
  #r = s.generate()
  
  for folder in ["SttrZyCK", "j7eLkrcV", "Gr9DGrs5", "4a7EsMTH"]:
    print(folder, end="")
    a = Audio(folder, open(f"./stories/{folder}/story.txt", "r").read())
    a.generate()
    print(" Done!")