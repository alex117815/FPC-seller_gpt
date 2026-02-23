from __future__ import annotations
from typing import TYPE_CHECKING, Optional
import logging

if TYPE_CHECKING:
    from cardinal import Cardinal

from FunPayAPI.updater.events import NewMessageEvent
from FunPayAPI.types import MessageTypes

from .config import PluginConfig
from .ai_manager import AIManager
from ..utils.lot_fetcher import LotInfoFetcher

logger = logging.getLogger("FPC.AIAssistant.Processor")


class MessageProcessor:
    def __init__(
        self,
        cardinal: Cardinal,
        ai_manager: AIManager,
        config: PluginConfig
    ):
        self._cardinal = cardinal
        self._ai_manager = ai_manager
        self._config = config
        self._lot_fetcher = LotInfoFetcher(cardinal)

    def _should_process(self, event: NewMessageEvent) -> bool:
        if not self._config.enabled:
            return False

        msg = event.message
        
        if msg.type != MessageTypes.NON_SYSTEM:
            return False
        
        if msg.author_id == self._cardinal.account.id:
            return False
        
        if msg.chat_name in self._cardinal.blacklist:
            if not self._config.handle_blacklisted:
                logger.debug(f"User {msg.chat_name} in blacklist")
                return False
        
        if "http" in msg.text.lower() or "https" in msg.text.lower():
            return False
        
        return True

    def _extract_question(self, text: str) -> Optional[str]:
        prefix = self._config.command_prefix.lower()
        text_lower = text.lower().strip()

        if not text_lower.startswith(prefix):
            return None

        question = text[len(prefix):].strip()
        return question if question else None

    def _is_reset_command(self, text: str) -> bool:
        return text.strip().lower() in ("!сброс", "!reset", "!clear")

    def process_message(self, event: NewMessageEvent) -> None:
        if not self._should_process(event):
            return

        text = event.message.text
        chat_id = event.message.chat_id

        if self._is_reset_command(text):
            self._ai_manager.clear_history(chat_id)
            self._lot_fetcher.clear_cache(chat_id)
            self._cardinal.send_message(chat_id, "История диалога сброшена.")
            logger.info(f"History reset for chat {chat_id}")
            return

        question = self._extract_question(text)
        if not question:
            return

        logger.info(f"Processing question from chat {chat_id}")

        context = self._lot_fetcher.get_lot_context(chat_id)

        response = self._ai_manager.generate_response(
            chat_id=chat_id,
            user_message=question,
            context=context,
        )

        if response:
            self._cardinal.send_message(chat_id, response)
            logger.info(f"Response sent to chat {chat_id}")
        else:
            logger.warning(f"Failed to generate response for chat {chat_id}")