"""Handler for receipt scanning via photo messages."""
import concurrent.futures
import logging

from handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
from services.expense_service import ExpenseService
from services.ocr_service import OcrService
from messages import (
    SCAN_PROMPT, SCAN_PROCESSING, SCAN_ERROR, SCAN_NO_TEXT,
    SCAN_CONFIRM, SCAN_CONFIRM_LOW_CONFIDENCE, ADD_CANCELLED,
    SCAN_EDIT_VALUE, SCAN_EDIT_NAME, SCAN_EDIT_DATE, SCAN_EDIT_INSTALLMENTS,
    SCAN_NO_AMOUNT, ADD_SUCCESS, VALUE_INVALID, VALUE_MUST_BE_POSITIVE,
    NAME_EMPTY, NAME_TOO_LONG, NAME_NOT_ALPHANUMERIC,
    INSTALLMENTS_INVALID, INSTALLMENTS_TOO_LARGE,
)
from utils.validators import ExpenseValidator
from telebot import types


class ReceiptHandler(BaseHandler):
    """Handles receipt scanning OCR flow."""

    def __init__(self, bot, state_manager,
                 expense_service: ExpenseService,
                 ocr_service: OcrService):
        super().__init__(bot, state_manager)
        self.expense_service = expense_service
        self.ocr = ocr_service
        self.validator = ExpenseValidator()

    _ERROR_MAP = {
        "VALUE_INVALID": VALUE_INVALID,
        "VALUE_MUST_BE_POSITIVE": VALUE_MUST_BE_POSITIVE,
        "NAME_EMPTY": NAME_EMPTY,
        "NAME_TOO_LONG": NAME_TOO_LONG,
        "NAME_NOT_ALPHANUMERIC": NAME_NOT_ALPHANUMERIC,
        "INSTALLMENTS_INVALID": INSTALLMENTS_INVALID,
        "INSTALLMENTS_TOO_LARGE": INSTALLMENTS_TOO_LARGE,
    }

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------

    def handle_scan_command(self, message) -> None:
        """Handle /foto command."""
        logger.info("User %d sent /foto command", message.from_user.id)
        if message.photo:
            self._process_photo(message)
        else:
            logger.info("No photo in /foto command, sending prompt")
            self.send_info(message.chat.id, SCAN_PROMPT)

    def handle_photo_message(self, message) -> None:
        """Handle any unsolicited photo message."""
        logger.info("User %d sent a photo", message.from_user.id)
        self._process_photo(message)

    # ------------------------------------------------------------------
    # Core OCR processing
    # ------------------------------------------------------------------

    def _ocr_and_parse(self, image_bytes: bytes) -> dict:
        """Run OCR extraction and receipt parsing (may include LLM inference)."""
        logger.info("=== OCR + PARSE START ===")
        ocr_results = self.ocr.extract_text(image_bytes)
        if not ocr_results:
            logger.warning("OCR returned no results")
            return {"empty": True}
        logger.info("OCR returned %d lines — sending to parser", len(ocr_results))
        result = self.ocr.parse_receipt(ocr_results)
        logger.info("=== OCR + PARSE END ===")
        return result

    def _process_photo(self, message) -> None:
        """Download photo, run OCR + AI parsing, show result with confirmation."""
        chat_id = message.chat.id
        user_id = message.from_user.id
        logger.info("=== RECEIPT FLOW START (user=%d) ===", user_id)

        status_msg = self.bot.send_message(chat_id, SCAN_PROCESSING)

        try:
            file_id = message.photo[-1].file_id
            file_info = self.bot.get_file(file_id)
            logger.info("Downloading photo file_id=%s", file_id)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                image_bytes = pool.submit(
                    self.bot.download_file, file_info.file_path
                ).result(timeout=30)
            logger.info("Photo downloaded (%d bytes)", len(image_bytes))
        except concurrent.futures.TimeoutError:
            logger.error("Photo download timed out")
            self.bot.edit_message_text(SCAN_ERROR, chat_id, status_msg.message_id)
            return
        except Exception as e:
            logger.error("Photo download failed: %s", e)
            self.bot.edit_message_text(SCAN_ERROR, chat_id, status_msg.message_id)
            import traceback
            traceback.print_exc()
            return

        try:
            logger.info("Starting OCR + parse (120s timeout)")
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                parsed = pool.submit(
                    self._ocr_and_parse, image_bytes
                ).result(timeout=120)
            logger.info("OCR + parse completed")
        except concurrent.futures.TimeoutError:
            logger.error("OCR + parse timed out after 120s")
            self.bot.edit_message_text(SCAN_ERROR, chat_id, status_msg.message_id)
            return
        except Exception as e:
            logger.error("OCR + parse failed: %s", e)
            self.bot.edit_message_text(SCAN_ERROR, chat_id, status_msg.message_id)
            import traceback
            traceback.print_exc()
            return

        if parsed.get("empty"):
            logger.warning("No text detected in image")
            self.bot.edit_message_text(SCAN_NO_TEXT, chat_id, status_msg.message_id)
            return

        self.state.set_receipt_state(user_id, {
            "step": "confirming",
            "parsed_data": parsed,
        })

        self.bot.delete_message(chat_id, status_msg.message_id)
        logger.info("Parsed data — amount=%s, store_name=%s, date=%s, conf=%.4f",
                     parsed.get("amount"), parsed.get("store_name"),
                     parsed.get("date"), parsed.get("confidence", 0))

        if parsed["amount"] is None:
            logger.info("No amount detected — starting manual input")
            self._start_manual_value(chat_id, user_id)
            return

        text = SCAN_CONFIRM.format(
            store_name=parsed["store_name"] or "Não identificado",
            amount=parsed["amount"],
            date=parsed["date"] or "Não identificada",
        )
        if parsed["confidence"] < 0.7:
            text += (
                "\n\n⚠️ *Confiança baixa.*\n"
                "📄 Texto reconhecido:\n```\n"
                + parsed["raw_text"]
                + "\n```"
            )

        keyboard = types.InlineKeyboardMarkup(row_width=3)
        keyboard.add(
            types.InlineKeyboardButton("Sim ✅", callback_data="RECEIPT_CONFIRM"),
            types.InlineKeyboardButton("Editar ✏️", callback_data="RECEIPT_EDIT"),
            types.InlineKeyboardButton("Cancelar ❌", callback_data="RECEIPT_CANCEL"),
        )
        self.bot.send_message(chat_id, text, parse_mode="Markdown",
                              reply_markup=keyboard)

    # ------------------------------------------------------------------
    # Callback handlers
    # ------------------------------------------------------------------

    def handle_confirm(self, call) -> None:
        """User confirmed the parsed data."""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        logger.info("User %d confirmed receipt data", user_id)

        receipt_state = self.state.get_receipt_state(user_id)
        if not receipt_state:
            logger.warning("User %d has no pending receipt state", user_id)
            self.bot.answer_callback_query(call.id, "Nenhum dado pendente.")
            return

        parsed = receipt_state.get("parsed_data", {})
        amount = parsed.get("amount")
        name = parsed.get("store_name", "Despesa")

        if amount is None:
            logger.warning("User %d confirmed but amount is None", user_id)
            self.bot.answer_callback_query(call.id, "Valor não identificado.")
            return

        self._save_and_finish(
            user_id, chat_id, call.message.message_id,
            name, amount, call,
            date=parsed.get("date"),
        )

    def handle_edit(self, call) -> None:
        """User wants to edit the parsed data -> start value edit."""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        logger.info("User %d started editing receipt data", user_id)
        receipt_state = self.state.get_receipt_state(user_id)
        parsed = receipt_state.get("parsed_data", {}) if receipt_state else {}
        current_amount = parsed.get("amount")

        self.state.update_receipt_state(user_id, "step", "editing_value")
        self.bot.edit_message_reply_markup(chat_id, call.message.message_id,
                                           reply_markup=None)
        if current_amount:
            msg = self.bot.send_message(
                chat_id, SCAN_EDIT_VALUE.format(current=current_amount),
                parse_mode="Markdown",
            )
        else:
            msg = self.bot.send_message(chat_id, "✏️ Digite o valor da despesa:")
        self.bot.register_next_step_handler(msg, self._handle_edit_value)
        self.bot.answer_callback_query(call.id)

    def handle_cancel_action(self, call) -> None:
        """User cancelled the receipt operation."""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        logger.info("User %d cancelled receipt operation", user_id)

        self.state.clear_receipt_state(user_id)
        self.bot.edit_message_reply_markup(chat_id, call.message.message_id,
                                           reply_markup=None)
        self.bot.send_message(chat_id, ADD_CANCELLED)
        self.bot.answer_callback_query(call.id, "Operação cancelada.")

    # ------------------------------------------------------------------
    # Edit step handlers (called via register_next_step_handler)
    # ------------------------------------------------------------------

    def _start_manual_value(self, chat_id: int, user_id: int) -> None:
        """Fallback when no amount was detected."""
        self.state.update_receipt_state(user_id, "step", "editing_value")
        msg = self.bot.send_message(chat_id, SCAN_NO_AMOUNT)
        self.bot.register_next_step_handler(msg, self._handle_edit_value)

    def _handle_edit_value(self, message) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        logger.info("User %d editing value: %s", user_id, message.text)
        receipt_state = self.state.get_receipt_state(user_id)
        parsed = receipt_state.get("parsed_data", {}) if receipt_state else {}

        if self.is_cancel_command(message.text):
            self.state.clear_receipt_state(user_id)
            self.handle_cancel(chat_id)
            return

        is_valid, value, error_key = self.validator.validate_value(message.text)
        if not is_valid:
            logger.warning("Invalid value input: %s (error=%s)", message.text, error_key)
            self.send_error(chat_id, self._ERROR_MAP.get(error_key, "Valor inválido"))
            msg = self.bot.send_message(chat_id, "✏️ Digite o valor da despesa:")
            self.bot.register_next_step_handler(msg, self._handle_edit_value)
            return

        logger.info("Value accepted: %.2f", value)
        self.state.update_receipt_state(user_id, "parsed_data", {
            **parsed,
            "amount": value,
        })
        self.state.update_receipt_state(user_id, "step", "editing_name")
        current_name = parsed.get("store_name") or "Despesa"
        msg = self.bot.send_message(
            chat_id, SCAN_EDIT_NAME.format(current=current_name),
            parse_mode="Markdown",
        )
        self.bot.register_next_step_handler(msg, self._handle_edit_name)

    def _handle_edit_name(self, message) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        logger.info("User %d editing name: %s", user_id, message.text)
        receipt_state = self.state.get_receipt_state(user_id)
        parsed = receipt_state.get("parsed_data", {}) if receipt_state else {}

        if self.is_cancel_command(message.text):
            self.state.clear_receipt_state(user_id)
            self.handle_cancel(chat_id)
            return

        name = message.text.strip()
        if not name:
            logger.warning("Empty name submitted")
            self.send_error(chat_id, NAME_EMPTY)
            current_name = parsed.get("store_name") or "Despesa"
            msg = self.bot.send_message(
                chat_id, SCAN_EDIT_NAME.format(current=current_name),
                parse_mode="Markdown",
            )
            self.bot.register_next_step_handler(msg, self._handle_edit_name)
            return

        logger.info("Name accepted: %s", name)
        self.state.update_receipt_state(user_id, "parsed_data", {
            **parsed,
            "store_name": name,
        })
        self.state.update_receipt_state(user_id, "step", "editing_date")
        current_date = parsed.get("date") or "não identificada"
        msg = self.bot.send_message(
            chat_id, SCAN_EDIT_DATE.format(current=current_date),
            parse_mode="Markdown",
        )
        self.bot.register_next_step_handler(msg, self._handle_edit_date)

    def _handle_edit_date(self, message) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        logger.info("User %d editing date: %s", user_id, message.text)
        receipt_state = self.state.get_receipt_state(user_id)
        parsed = receipt_state.get("parsed_data", {}) if receipt_state else {}

        if self.is_cancel_command(message.text):
            self.state.clear_receipt_state(user_id)
            self.handle_cancel(chat_id)
            return

        import re
        date_pattern = re.compile(r'^\d{2}-\d{2}-\d{4}$')
        if not date_pattern.match(message.text.strip()):
            logger.warning("Invalid date format: %s", message.text)
            self.send_error(chat_id, "❌ Data inválida! Use o formato DD-MM-YYYY.")
            current_date = parsed.get("date") or "não identificada"
            msg = self.bot.send_message(
                chat_id, SCAN_EDIT_DATE.format(current=current_date),
                parse_mode="Markdown",
            )
            self.bot.register_next_step_handler(msg, self._handle_edit_date)
            return

        logger.info("Date accepted: %s", message.text.strip())
        self.state.update_receipt_state(user_id, "parsed_data", {
            **parsed,
            "date": message.text.strip(),
        })
        self.state.update_receipt_state(user_id, "step", "editing_installments")
        current_inst = parsed.get("installments", 1)
        msg = self.bot.send_message(
            chat_id, SCAN_EDIT_INSTALLMENTS.format(current=current_inst),
            parse_mode="Markdown",
        )
        self.bot.register_next_step_handler(msg, self._handle_edit_installments)

    def _handle_edit_installments(self, message) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        logger.info("User %d editing installments: %s", user_id, message.text)
        receipt_state = self.state.get_receipt_state(user_id)
        parsed = receipt_state.get("parsed_data", {}) if receipt_state else {}

        if self.is_cancel_command(message.text):
            self.state.clear_receipt_state(user_id)
            self.handle_cancel(chat_id)
            return

        is_valid, installments, error_key = self.validator.validate_installments(
            message.text
        )
        if not is_valid:
            logger.warning("Invalid installments: %s (error=%s)", message.text, error_key)
            self.send_error(chat_id, self._ERROR_MAP.get(error_key,
                            "Número de parcelas inválido"))
            current_inst = parsed.get("installments", 1)
            msg = self.bot.send_message(
                chat_id, SCAN_EDIT_INSTALLMENTS.format(current=current_inst),
                parse_mode="Markdown",
            )
            self.bot.register_next_step_handler(msg,
                                                 self._handle_edit_installments)
            return

        logger.info("Installments accepted: %d", installments)
        self.state.update_receipt_state(user_id, "parsed_data", {
            **parsed,
            "installments": installments,
        })

        final = self.state.get_receipt_state(user_id).get("parsed_data", {})
        self._save_and_finish(
            user_id, chat_id, None,
            final.get("store_name", "Despesa"),
            final.get("amount", 0.0),
            installments=installments,
            date=final.get("date"),
        )

    # ------------------------------------------------------------------
    # Save helper
    # ------------------------------------------------------------------

    def _save_and_finish(self, user_id: int, chat_id: int,
                         message_id: int = None, name: str = "Despesa",
                         amount: float = 0.0, call=None,
                         installments: int = 1, date: str = None) -> None:
        """Save expense and clean up state."""
        logger.info("=== SAVING EXPENSE ===")
        logger.info("user=%d, name=%s, amount=%.2f, installments=%d, date=%s",
                     user_id, name, amount, installments, date or "today")
        try:
            self.expense_service.create_expense(
                user_id=user_id,
                name=name,
                amount=amount,
                installments=installments,
                date=date,
            )
            logger.info("Expense saved successfully")
        except Exception as e:
            logger.error("Failed to save expense: %s", e)
            self.send_error(chat_id,
                            f"❌ Erro ao salvar despesa: {str(e)[:100]}")
            self.state.clear_receipt_state(user_id)
            return

        self.state.clear_receipt_state(user_id)

        if message_id:
            try:
                self.bot.edit_message_reply_markup(
                    chat_id, message_id, reply_markup=None)
            except Exception:
                pass

        success_msg = ADD_SUCCESS.format(
            name=name,
            value=float(amount),
            date=date or "hoje",
            installments=installments,
        )
        self.bot.send_message(chat_id, success_msg)

        if call:
            self.bot.answer_callback_query(call.id, "Despesa registrada!")
        logger.info("=== RECEIPT FLOW END ===")
