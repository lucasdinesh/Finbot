"""Handler for /insights command."""
from datetime import datetime
from handlers.base_handler import BaseHandler
from services.expense_service import ExpenseService
from messages import (
    INSIGHT_HEADER, INSIGHT_TOTAL, INSIGHT_COUNT, INSIGHT_CATEGORY_LINE,
    INSIGHT_NO_DATA, INSIGHT_ARROW_UP, INSIGHT_ARROW_DOWN, INSIGHT_ARROW_SAME,
    INSIGHT_NEW, INSIGHT_NONE, MONTH_NAMES,
)


class InsightHandler(BaseHandler):

    def __init__(self, bot, state_manager, expense_service: ExpenseService):
        super().__init__(bot, state_manager)
        self.expense_service = expense_service

    def handle_insights(self, message) -> None:
        now = datetime.now()
        user_id = message.from_user.id
        current_month = now.month
        current_year = now.year

        if current_month == 1:
            prev_month = 12
            prev_year = current_year - 1
        else:
            prev_month = current_month - 1
            prev_year = current_year

        current_expenses = self.expense_service.get_expenses_by_month(user_id, current_year, current_month)
        prev_expenses = self.expense_service.get_expenses_by_month(user_id, prev_year, prev_month)

        if not current_expenses and not prev_expenses:
            self.send_info(message.chat.id, INSIGHT_NO_DATA)
            return

        current_total = sum(e.amount for e in current_expenses)
        prev_total = sum(e.amount for e in prev_expenses)

        total_change = 0.0
        if prev_total > 0:
            total_change = ((current_total - prev_total) / prev_total) * 100

        text = INSIGHT_HEADER.format(
            month=MONTH_NAMES[current_month - 1],
            prev_month=MONTH_NAMES[prev_month - 1],
        )
        text += INSIGHT_TOTAL.format(total=current_total, change=total_change)
        text += INSIGHT_COUNT.format(
            count=len(current_expenses),
            count_change=len(current_expenses) - len(prev_expenses),
        )

        categories = self.expense_service.get_categories(user_id)
        cat_map = dict(categories)
        cat_map[None] = "Sem categoria"

        current_by_cat: dict = {}
        for e in current_expenses:
            key = e.category_id or -1
            current_by_cat[key] = current_by_cat.get(key, 0) + e.amount

        prev_by_cat: dict = {}
        for e in prev_expenses:
            key = e.category_id or -1
            prev_by_cat[key] = prev_by_cat.get(key, 0) + e.amount

        all_keys = sorted(set(list(current_by_cat.keys()) + list(prev_by_cat.keys())))

        for key in all_keys:
            c_amt = current_by_cat.get(key, 0)
            p_amt = prev_by_cat.get(key, 0)
            cat_name = cat_map.get(key if key != -1 else None, "Sem categoria")

            if p_amt == 0 and c_amt > 0:
                change_str = INSIGHT_NEW
                arrow = INSIGHT_ARROW_UP
            elif p_amt > 0:
                pct = ((c_amt - p_amt) / p_amt) * 100
                arrow = INSIGHT_ARROW_UP if pct > 0 else (INSIGHT_ARROW_DOWN if pct < 0 else INSIGHT_ARROW_SAME)
                change_str = f"{pct:+.1f}%"
            else:
                change_str = INSIGHT_NONE
                arrow = INSIGHT_ARROW_SAME

            text += INSIGHT_CATEGORY_LINE.format(
                category=cat_name,
                amount=c_amt,
                change=change_str,
                arrow=arrow,
            )

        self.send_info(message.chat.id, text)
