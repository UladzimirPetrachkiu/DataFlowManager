# src/bot.py

from typing import Set
import sqlite3
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from src.config import TELEGRAM_BOT_TOKEN

class TelegramBot:
    """A simple Telegram bot that manages subscriptions for notifications."""

    def __init__(self, token: str) -> None:
        """
        Initializes the TelegramBot with the given token.

        Args:
            token (str): The token provided by Telegram to access the bot's API.
        """
        self.bot = Bot(token=token)
        self.db_file = 'db/subscribers.db'
        self.create_table()

    def create_table(self) -> None:
        """
        Creates a subscribers table if it doesn't exist.

        Creates a SQLite database table named 'subscribers' with a single column
        'user_id' as the primary key.
        """
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscribers (
                    user_id INTEGER PRIMARY KEY
                )
            ''')
            conn.commit()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Sends a welcome message when the /start command is issued.

        Args:
            update (Update): An object containing information about the update
                            received by the bot.
            context (ContextTypes.DEFAULT_TYPE): A context object containing
                                                information about the current
                                                interaction.
        """
        await update.message.reply_text("Welcome! Use /subscribe to receive notifications.")

    async def subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Subscribes the user to notifications.

        Args:
            update (Update): An object containing information about the update
                            received by the bot.
            context (ContextTypes.DEFAULT_TYPE): A context object containing
                                                information about the current
                                                interaction.
        """
        user_id = update.message.chat_id
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)', (user_id,))
            conn.commit()
        await update.message.reply_text("You've subscribed to notifications!")

    async def unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Unsubscribes the user from notifications.

        Args:
            update (Update): An object containing information about the update
                            received by the bot.
            context (ContextTypes.DEFAULT_TYPE): A context object containing
                                                information about the current
                                                interaction.
        """
        user_id = update.message.chat_id
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM subscribers WHERE user_id = ?', (user_id,))
            conn.commit()
        await update.message.reply_text("You've unsubscribed from notifications.")

    def get_subscribers(self) -> Set[int]:
        """
        Fetches all subscribers from the database.

        Returns:
            Set[int]: A set containing the IDs of all subscribers.
        """
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM subscribers')
            return {row[0] for row in cursor.fetchall()}

    async def send_notification(self, message: str) -> None:
        """
        Sends a notification message to all subscribers.

        Args:
            message (str): The message to be sent as a notification.
        """
        subscribers = self.get_subscribers()
        for user_id in subscribers:
            try:
                await self.bot.send_message(chat_id=user_id, text=message)
            except Exception as e:
                print(f"Error sending message to {user_id}: {e}")

    def run(self) -> None:
        """
        Starts the bot and listens for commands.

        Creates an Application object using the bot's token and adds
        CommandHandler instances for the '/start', '/subscribe', and
        '/unsubscribe' commands. Then, it runs the bot's polling mechanism to
        listen for updates.
        """
        application = Application.builder().token(self.bot.token).build()
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("subscribe", self.subscribe))
        application.add_handler(CommandHandler("unsubscribe", self.unsubscribe))
        application.run_polling()

telegram_bot = TelegramBot(token=TELEGRAM_BOT_TOKEN)

def run_bot() -> None:
    """Function to run the Telegram bot. Starts the Telegram bot by calling its 'run' method."""
    telegram_bot.run()
