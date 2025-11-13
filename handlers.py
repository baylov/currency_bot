from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

router = Router()


@router.message(Command("start"))
async def handle_start(message: Message) -> None:
    """Handle /start command."""
    await message.answer(
        "Welcome to the bot! 🚀\n\n"
        "This is a template for an async Telegram bot with APScheduler support.\n"
        "Use /help to see available commands."
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Handle /help command."""
    help_text = (
        "📋 Available commands:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/status - Check bot status"
    )
    await message.answer(help_text)


@router.message(Command("status"))
async def handle_status(message: Message) -> None:
    """Handle /status command."""
    await message.answer("✅ Bot is running normally!")


@router.message()
async def handle_unknown_message(message: Message) -> None:
    """Handle unknown messages."""
    await message.answer(
        "I don't understand this command. Use /help to see available commands."
    )