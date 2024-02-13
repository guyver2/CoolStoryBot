import logging

from telegram import ForceReply, Update, Message
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from oai import Story, WITH_AUDIO
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN', '')



# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# stores all pending requests.
pending_requests: set[Message]= set()
allowed_users = [XXXXXX]

async def storyInitiator(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  if update.message is not None:
    user = update.effective_user
    if user is None or user.id not in allowed_users:
      logging.warning(f'Unknow user request. ID:{user.id}, name {user.username}')
      message = await update.message.reply_html(f"Sorry, you are not allowed to use this bot.")
      return
    message = await update.message.reply_html(
            rf"Please reply to this message with plot of your story.",
            reply_markup=ForceReply(selective=True),
        )
    pending_requests.add(message)


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    if (message := update.message) is not None:
      if (rep_to := message.reply_to_message) is not None:
         if rep_to in pending_requests:
            if message.text:
              story = Story(message.text)
              await message.reply_html(f"Starting creation of new story with id: <b>{story.story_id}</b>. It can take a few minutes.")
              story.generate()
              with open(f"./stories/{story.story_id}/cover.png", "rb") as fd:
                await message.reply_photo(photo=fd)
              await message.reply_html(f"<b>{story.title}</b>\n\n{story.text}")
              if WITH_AUDIO:
                with open(f"./stories/{story.story_id}/audio.mp3", "rb") as fd:
                  await message.reply_audio(audio=fd)
            else:
               await message.reply_html(f"Can't generate a story with an empty plot.")
      else:     
        await message.reply_text("Not sure what I should do with that. please use /story to create a new story.")


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("story", storyInitiator))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()