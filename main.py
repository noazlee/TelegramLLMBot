import os
import logging
import pandas as pd
import numpy as np
from questions import answer_question
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, ApplicationBuilder, MessageHandler, filters
from openai import OpenAI
import asyncio
import nest_asyncio
import requests
import time

from functions import functions, run_function
import json

CODE_PROMPT = """
Here are two input:output examples for code generation. Please use these and follow the styling for future requests that you think are pertinent to the request.
Make sure All HTML is generated with the JSX flavoring.
// SAMPLE 1
// A Blue Box with 3 yellow cirles inside of it that have a red outline
<div style={{   backgroundColor: 'blue',
  padding: '20px',
  display: 'flex',
  justifyContent: 'space-around',
  alignItems: 'center',
  width: '300px',
  height: '100px', }}>
  <div style={{     backgroundColor: 'yellow',
    borderRadius: '50%',
    width: '50px',
    height: '50px',
    border: '2px solid red'
  }}></div>
  <div style={{     backgroundColor: 'yellow',
    borderRadius: '50%',
    width: '50px',
    height: '50px',
    border: '2px solid red'
  }}></div>
  <div style={{     backgroundColor: 'yellow',
    borderRadius: '50%',
    width: '50px',
    height: '50px',
    border: '2px solid red'
  }}></div>
</div>
""" 

nest_asyncio.apply()

df = pd.read_csv('processed/embeddings.csv', index_col=0)
df['embeddings'] = df['embeddings'].apply(eval).apply(np.array)

openai = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
tg_bot_token = os.environ['TG_BOT_TOKEN']

assistant = openai.beta.assistants.create(
    name="Telegram Bot",
    instructions=CODE_PROMPT,
    tools=[
    {"type": "code_interpreter"},
    ],
    model="gpt-4-0125-preview",
)

THREAD = openai.beta.threads.create()

logging.basicConfig(
    format='%(asctime)s - %(name)s - $(levelname)s - %(message)s',
    level=logging.INFO
)

def wait_on_run(run, thread):
    while run.status in ("queued", "in_progress"):
        print(run.status)
        run = openai.beta.threads.runs.retrieve(
        thread_id=thread.id,
        run_id=run.id,
        )
        time.sleep(0.5)
    return run

async def assistant_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = openai.beta.threads.messages.create(
    thread_id=THREAD.id, role="user", content=update.message.text
    )
    run = openai.beta.threads.runs.create(
    thread_id=THREAD.id, assistant_id=assistant.id
    )
    run = wait_on_run(run, THREAD)
    # Grab all of our message history
    messages = openai.beta.threads.messages.list(
    thread_id=THREAD.id, order="asc", after=message.id
    )
    # Extract the message content
    message_content = messages.data[0].content[0].text
    await context.bot.send_message(
    chat_id=update.effective_chat.id, text=message_content.value
    )

async def mozilla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = answer_question(df, question=update.message.text, debug=True)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=answer)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                  text="I am a bot, please talk to me.")
    
async def image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = openai.images.generate(prompt=update.message.text,
                                    model="dall-e-3",
                                    n=1,
                                    size="1024x1024")
    image_url = response.data[0].url
    image_response = requests.get(image_url)
    await context.bot.send_photo(chat_id=update.effective_chat.id,
                               photo=image_response.content)

async def transcribe_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Make sure we have a voice file to transcribe
    voice_id = update.message.voice.file_id
    if voice_id:
        file = await context.bot.get_file(voice_id)
        await file.download_to_drive(f"voice_note_{voice_id}.ogg")
        await update.message.reply_text("Voice note downloaded, transcribing now")
        audio_file = open(f"voice_note_{voice_id}.ogg", "rb")
        transcript = openai.audio.transcriptions.create(
        model="whisper-1", file=audio_file
        )
        messages.append({"role": "user", "content": transcript.text})
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        # Feed it back into the LLM
        response_message = response.choices[0].message
        messages.append(response_message)
        await update.message.reply_text(f"Transcript finished:\n{transcript.text}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response_message.content)

# Main function to run the bot
async def main() -> None:
    application = ApplicationBuilder().token(tg_bot_token).build()

    start_handler = CommandHandler('start', start)
    chat_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), assistant_chat)
    image_handler = CommandHandler('image', image)
    mozilla_handler = CommandHandler('mozilla', mozilla)
    voice_handler = MessageHandler(filters.VOICE, transcribe_message)

    application.add_handler(start_handler)
    application.add_handler(chat_handler)
    application.add_handler(image_handler)
    application.add_handler(mozilla_handler)
    application.add_handler(voice_handler)

    await application.run_polling()

# Check if the script is run directly (not imported)
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if str(e) == "asyncio.run() cannot be called from a running event loop":
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
        else:
            raise
        
