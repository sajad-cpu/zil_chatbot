"""Main entry point for the Clinic Booking Chatbot."""

from data.db import init_db
from ui.chat_ui import run_chat_ui

if __name__ == "__main__":
    init_db()
    run_chat_ui()
