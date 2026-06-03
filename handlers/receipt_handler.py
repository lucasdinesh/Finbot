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
    ADD_PAYMENT_PROMPT, PAYMENT_PIX, PAYMENT_DINHEIRO, PAYMENT_CREDITO,
    ADD_CATEGORY_PROMPT, ADD_CATEGORY_CUSTOM_PROMPT, CATEGORY_OTHER,
)
from utils.validators import ExpenseValidator
from telebot import types, formatting


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

    PAYMENT_METHODS = {
        "RCPAYMENT_PIX": "pix",
        "RCPAYMENT_DINHEIRO": "dinheiro",
        "RCPAYMENT_CREDITO": "credito",
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
                ).result(timeout=60)
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
            logger.info("Starting OCR + parse")
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self._ocr_and_parse, image_bytes)
                try:
                    parsed = future.result(timeout=180)
                except concurrent.futures.TimeoutError:
                    if future.done():
                        parsed = future.result()
                    else:
                        raise
            logger.info("OCR + parse completed")
        except concurrent.futures.TimeoutError:
            logger.error("OCR + parse timed out after 180s")
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
            store_name=formatting.escape_markdown(parsed["store_name"] or "Não identificado"),
            amount=parsed["amount"],
            date=parsed["date"] or "Não identificada",
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

        self.state.update_receipt_state(user_id, "message_id", call.message.message_id)
        self._ask_receipt_payment(chat_id, user_id, call)

    def handle_edit(self, call) -> None:
        """User wants to edit the parsed data -> show field selection."""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        logger.info("User %d started editing receipt data", user_id)

        receipt_state = self.state.get_receipt_state(user_id)
        if not receipt_state:
            self.bot.answer_callback_query(call.id, "Nenhum dado pendente.")
            return

        self.state.update_receipt_state(user_id, "step", "field_selection")
        self.bot.edit_message_reply_markup(chat_id, call.message.message_id,
                                           reply_markup=None)
        self._show_edit_field_selection(chat_id, user_id)
        self.bot.answer_callback_query(call.id)

    def handle_edit_field(self, call) -> None:
        """Handle field selection callback from edit flow."""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        logger.info("User %d selected field: %s", user_id, call.data)

        receipt_state = self.state.get_receipt_state(user_id)
        if not receipt_state:
            self.bot.answer_callback_query(call.id, "Nenhum dado pendente.")
            return

        parsed = receipt_state.get("parsed_data", {})

        if call.data == "RECEIPT_EDIT_FIELD_VALUE":
            self.bot.edit_message_reply_markup(chat_id, call.message.message_id,
                                               reply_markup=None)
            self.state.update_receipt_state(user_id, "step", "editing_value")
            current_amount = parsed.get("amount")
            if current_amount:
                msg = self.bot.send_message(
                    chat_id, SCAN_EDIT_VALUE.format(current=current_amount),
                    parse_mode="Markdown",
                )
            else:
                msg = self.bot.send_message(chat_id, "✏️ Digite o valor da despesa:")
            self.bot.register_next_step_handler(msg, self._handle_edit_value)

        elif call.data == "RECEIPT_EDIT_FIELD_NAME":
            self.bot.edit_message_reply_markup(chat_id, call.message.message_id,
                                               reply_markup=None)
            self.state.update_receipt_state(user_id, "step", "editing_name")
            current_name = formatting.escape_markdown(parsed.get("store_name") or "Despesa")
            msg = self.bot.send_message(
                chat_id, SCAN_EDIT_NAME.format(current=current_name),
                parse_mode="Markdown",
            )
            self.bot.register_next_step_handler(msg, self._handle_edit_name)

        elif call.data == "RECEIPT_EDIT_FIELD_DATE":
            self.bot.edit_message_reply_markup(chat_id, call.message.message_id,
                                               reply_markup=None)
            self.state.update_receipt_state(user_id, "step", "editing_date")
            current_date = parsed.get("date") or "não identificada"
            msg = self.bot.send_message(
                chat_id, SCAN_EDIT_DATE.format(current=current_date),
                parse_mode="Markdown",
            )
            self.bot.register_next_step_handler(msg, self._handle_edit_date)

        elif call.data == "RECEIPT_EDIT_DONE":
            self.state.update_receipt_state(user_id, "step", "awaiting_payment")
            self._ask_receipt_payment(chat_id, user_id, call)

        self.bot.answer_callback_query(call.id)

    def _show_edit_field_selection(self, chat_id: int, user_id: int) -> None:
        """Show inline buttons for which field to edit."""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("Valor 💵", callback_data="RECEIPT_EDIT_FIELD_VALUE"),
            types.InlineKeyboardButton("Estabelecimento 🏪", callback_data="RECEIPT_EDIT_FIELD_NAME"),
            types.InlineKeyboardButton("Data 📅", callback_data="RECEIPT_EDIT_FIELD_DATE"),
            types.InlineKeyboardButton("Pronto ✅", callback_data="RECEIPT_EDIT_DONE"),
        )
        self.bot.send_message(chat_id, "✏️ Escolha o campo que deseja corrigir:",
                              reply_markup=keyboard)

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
    # Payment & category selection for receipt flow
    # ------------------------------------------------------------------

    def _ask_receipt_payment(self, chat_id: int, user_id: int, call=None) -> None:
        """Ask payment method before saving."""
        if call:
            self.bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
            self.bot.answer_callback_query(call.id)
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton(PAYMENT_PIX, callback_data="RCPAYMENT_PIX"),
            types.InlineKeyboardButton(PAYMENT_DINHEIRO, callback_data="RCPAYMENT_DINHEIRO"),
            types.InlineKeyboardButton(PAYMENT_CREDITO, callback_data="RCPAYMENT_CREDITO"),
        )
        self.state.update_receipt_state(user_id, "step", "awaiting_payment")
        self.bot.send_message(chat_id, ADD_PAYMENT_PROMPT, reply_markup=keyboard)

    def handle_receipt_payment_callback(self, call) -> None:
        """Handle payment method selection in receipt flow."""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        payment_method = self.PAYMENT_METHODS.get(call.data)
        if not payment_method:
            return

        logger.info("User %d selected payment: %s", user_id, payment_method)
        self.state.update_receipt_state(user_id, "payment_method", payment_method)
        self.state.update_receipt_state(user_id, "step", "awaiting_category")
        self.bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

        if payment_method == "credito":
            self.state.update_receipt_state(user_id, "step", "awaiting_installments")
            msg = self.bot.send_message(chat_id, "Quantas parcelas? (1-1000):")
            self.bot.register_next_step_handler(msg, self._handle_receipt_installments)
            self.bot.answer_callback_query(call.id)
            return
        else:
            self.state.update_receipt_state(user_id, "parsed_data", {
                **self.state.get_receipt_state(user_id).get("parsed_data", {}),
                "installments": 1,
            })

        self._ask_receipt_category(chat_id, user_id)
        self.bot.answer_callback_query(call.id)

    def _handle_receipt_installments(self, message) -> None:
        """Handle installment input when credit is selected in receipt flow."""
        user_id = message.from_user.id
        chat_id = message.chat.id

        if self.is_cancel_command(message.text):
            self.state.clear_receipt_state(user_id)
            self.handle_cancel(chat_id)
            return

        is_valid, installments, error_key = self.validator.validate_installments(message.text)
        if not is_valid:
            self.send_error(chat_id, self._ERROR_MAP.get(error_key, "Número de parcelas inválido"))
            msg = self.bot.send_message(chat_id, "Quantas parcelas? (1-1000):")
            self.bot.register_next_step_handler(msg, self._handle_receipt_installments)
            return

        self.state.update_receipt_state(user_id, "parsed_data", {
            **self.state.get_receipt_state(user_id).get("parsed_data", {}),
            "installments": installments,
        })
        self._ask_receipt_category(chat_id, user_id)

    def _ask_receipt_category(self, chat_id: int, user_id: int) -> None:
        """Show category inline buttons."""
        categories = self.expense_service.get_categories(user_id)
        self.state.update_receipt_state(user_id, "categories_data", categories)
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        for cat_id, cat_name in categories:
            keyboard.add(
                types.InlineKeyboardButton(cat_name, callback_data=f"RCCAT_{cat_id}")
            )
        keyboard.add(
            types.InlineKeyboardButton(CATEGORY_OTHER, callback_data="RCCAT_OTHER")
        )
        self.bot.send_message(chat_id, ADD_CATEGORY_PROMPT, reply_markup=keyboard)

    def handle_receipt_category_callback(self, call) -> None:
        """Handle category selection in receipt flow."""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        receipt_state = self.state.get_receipt_state(user_id)
        if not receipt_state:
            self.bot.answer_callback_query(call.id, "Nenhum dado pendente.")
            return

        if call.data == "RCCAT_OTHER":
            self.bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
            msg = self.bot.send_message(chat_id, ADD_CATEGORY_CUSTOM_PROMPT)
            self.bot.register_next_step_handler(msg, self._handle_custom_category)
            self.bot.answer_callback_query(call.id)
            return

        category_id = int(call.data.replace("RCCAT_", ""))
        self.state.update_receipt_state(user_id, "category_id", category_id)
        self.bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
        self.bot.answer_callback_query(call.id)

        self._finalize_receipt_expense(chat_id, user_id, call)

    def _handle_custom_category(self, message) -> None:
        """Handle custom category name from receipt flow."""
        name = message.text.strip()
        chat_id = message.chat.id
        user_id = message.from_user.id

        if self.is_cancel_command(name):
            self.state.clear_receipt_state(user_id)
            self.handle_cancel(chat_id)
            return

        if not name:
            self.send_error(chat_id, NAME_EMPTY)
            msg = self.bot.send_message(chat_id, ADD_CATEGORY_CUSTOM_PROMPT)
            self.bot.register_next_step_handler(msg, self._handle_custom_category)
            return

        if len(name) > 50:
            self.send_error(chat_id, NAME_TOO_LONG)
            msg = self.bot.send_message(chat_id, ADD_CATEGORY_CUSTOM_PROMPT)
            self.bot.register_next_step_handler(msg, self._handle_custom_category)
            return

        category_id = self.expense_service.create_category(name, user_id)
        self.state.update_receipt_state(user_id, "category_id", category_id)
        self._finalize_receipt_expense(chat_id, user_id)

    def _finalize_receipt_expense(self, chat_id: int, user_id: int, call=None) -> None:
        """Save expense after payment + category are selected."""
        receipt_state = self.state.get_receipt_state(user_id)
        parsed = receipt_state.get("parsed_data", {})
        payment_method = receipt_state.get("payment_method")
        category_id = receipt_state.get("category_id")
        message_id = receipt_state.get("message_id")

        self._save_and_finish(
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            name=parsed.get("store_name", "Despesa"),
            amount=parsed.get("amount", 0.0),
            call=call,
            installments=parsed.get("installments", 1),
            date=parsed.get("date"),
            category_id=category_id,
            payment_method=payment_method,
        )

    # ------------------------------------------------------------------
    # Edit step handlers (called via register_next_step_handler)
    # ------------------------------------------------------------------

    def _start_manual_value(self, chat_id: int, user_id: int) -> None:
        """Fallback when no amount was detected."""
        self.state.update_receipt_state(user_id, "step", "editing_value")
        msg = self.bot.send_message(chat_id, SCAN_NO_AMOUNT)
        self.bot.register_next_step_handler(msg, self._handle_edit_value)

    @staticmethod
    def _is_accept(text: str) -> bool:
        return text.strip().lower() in ("ok", "okay", "sim", "s", "keep")

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
            current_amount = parsed.get("amount")
            if current_amount:
                msg = self.bot.send_message(
                    chat_id, SCAN_EDIT_VALUE.format(current=current_amount),
                    parse_mode="Markdown",
                )
            else:
                msg = self.bot.send_message(chat_id, "✏️ Digite o valor da despesa:")
            self.bot.register_next_step_handler(msg, self._handle_edit_value)
            return
        logger.info("Value accepted: %.2f", value)

        self.state.update_receipt_state(user_id, "parsed_data", {
            **parsed,
            "amount": value,
        })
        self._show_edit_field_selection(chat_id, user_id)

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
            current_name = formatting.escape_markdown(parsed.get("store_name") or "Despesa")
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
        self._show_edit_field_selection(chat_id, user_id)

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

        from datetime import datetime
        import re
        date_str = message.text.strip().lower()

        if date_str == "hoje":
            date_str = datetime.now().strftime("%d-%m-%Y")
        else:
            date_pattern = re.compile(r'^\d{2}-\d{2}-\d{4}$')
            if not date_pattern.match(date_str):
                logger.warning("Invalid date format: %s", message.text)
                self.send_error(chat_id, "❌ Data inválida! Use o formato DD-MM-YYYY ou 'hoje'.")
                current_date = parsed.get("date") or "não identificada"
                msg = self.bot.send_message(
                    chat_id, SCAN_EDIT_DATE.format(current=current_date),
                    parse_mode="Markdown",
                )
                self.bot.register_next_step_handler(msg, self._handle_edit_date)
                return

        selected = datetime.strptime(date_str, "%d-%m-%Y")
        if selected.date() > datetime.now().date():
            self.send_error(chat_id, "❌ Data no futuro não permitida! Escolha uma data até hoje.")
            current_date = parsed.get("date") or "não identificada"
            msg = self.bot.send_message(
                chat_id, SCAN_EDIT_DATE.format(current=current_date),
                parse_mode="Markdown",
            )
            self.bot.register_next_step_handler(msg, self._handle_edit_date)
            return

        logger.info("Date accepted: %s", date_str)
        self.state.update_receipt_state(user_id, "parsed_data", {
            **parsed,
            "date": date_str,
        })
        self._show_edit_field_selection(chat_id, user_id)

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

        if self._is_accept(message.text):
            installments = parsed.get("installments", 1)
            logger.info("Installments kept: %d", installments)
        else:
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

        self._ask_receipt_payment(chat_id, user_id)

    # ------------------------------------------------------------------
    # Save helper
    # ------------------------------------------------------------------

    def _save_and_finish(self, user_id: int, chat_id: int,
                         message_id: int = None, name: str = "Despesa",
                         amount: float = 0.0, call=None,
                         installments: int = 1, date: str = None,
                         category_id: int = None,
                         payment_method: str = None) -> None:
        """Save expense and clean up state."""
        logger.info("=== SAVING EXPENSE ===")
        logger.info("user=%d, name=%s, amount=%.2f, installments=%d, date=%s, category=%s, payment=%s",
                     user_id, name, amount, installments, date or "today", category_id, payment_method)
        try:
            alert = self.expense_service.create_expense(
                user_id=user_id,
                name=name,
                amount=amount,
                installments=installments,
                date=date,
                category_id=category_id,
                payment_method=payment_method,
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

        if payment_method == "credito" and installments > 1:
            inst_line = f"Parcelas: {installments}"
        else:
            inst_line = ""

        success_msg = ADD_SUCCESS.format(
            name=name,
            value=float(amount),
            date=date or "hoje",
            installments_line=inst_line,
        )
        self.bot.send_message(chat_id, success_msg)

        if alert:
            self.send_warning(chat_id, alert)

        if call:
            self.bot.answer_callback_query(call.id, "Despesa registrada!")
        logger.info("=== RECEIPT FLOW END ===")
