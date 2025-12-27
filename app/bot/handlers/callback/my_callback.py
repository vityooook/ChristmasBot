from aiogram.filters.callback_data import CallbackData


class GiveawayCallback(CallbackData, prefix="giveaway"):
    """Callback для розыгрыша подарков."""
    act: str  # check_conditions, claim_gift
