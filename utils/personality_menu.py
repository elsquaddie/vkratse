"""
Universal personality menu builder
Provides consistent UI across all personality selection contexts
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Optional, Dict, Any
from services import DBService
from utils import create_string_signature


def build_personality_menu(
    user_id: int,
    callback_prefix: str,
    context: str = "select",
    current_personality: Optional[str] = None,
    extra_callback_data: Optional[Dict[str, Any]] = None,
    show_create_button: bool = True,
    show_back_button: bool = False,
    back_callback: str = "back_to_main"
) -> InlineKeyboardMarkup:
    """
    Build universal personality selection menu with consistent UX.

    Args:
        user_id: User ID for fetching custom personalities
        callback_prefix: Prefix for callback_data (e.g., "pers:select", "summary_personality")
        context: Menu context - "manage" (with edit/delete) or "select" (only selection)
        current_personality: Name of currently selected personality (for ✓ indicator)
        extra_callback_data: Extra data to include in callback (e.g., {"chat_id": 123, "limit": "50"})
        show_create_button: Whether to show "Create personality" button
        show_back_button: Whether to show "Back" button
        back_callback: Callback data for back button (default: "back_to_main")

    Returns:
        InlineKeyboardMarkup with personality selection buttons

    Examples:
        # For /lichnost (management context)
        build_personality_menu(
            user_id=123,
            callback_prefix="pers:select",
            context="manage",
            current_personality="bydlan"
        )

        # For /summary (selection context)
        build_personality_menu(
            user_id=123,
            callback_prefix="summary_personality",
            context="select",
            current_personality="bydlan",
            extra_callback_data={"chat_id": 456, "limit": "none"}
        )
    """
    from utils.security import sign_callback_data

    db = DBService()
    keyboard = []

    # 1. Get all personalities (base + user's custom)
    all_personalities = db.get_all_personalities()

    if not all_personalities:
        # Fallback for empty DB
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Личности не найдены", callback_data="pers:noop")
        ]])

    # 2. Split into base and custom
    base_personalities = [p for p in all_personalities if not p.is_custom]
    custom_personalities = [
        p for p in all_personalities
        if p.is_custom and p.created_by_user_id == user_id
    ]

    # 3. Build keyboard for base personalities (2 columns)
    row = []
    for p in base_personalities:
        button_text = f"{p.emoji} {p.display_name}"
        if current_personality and p.name == current_personality:
            button_text += " ✓"

        callback_data = _build_callback_data(
            callback_prefix,
            p,
            user_id,
            extra_callback_data
        )

        row.append(InlineKeyboardButton(button_text, callback_data=callback_data))

        if len(row) == 2:
            keyboard.append(row)
            row = []

    # Add remaining button if odd number
    if row:
        keyboard.append(row)

    # 4. Custom personalities section
    if custom_personalities:
        # Section header
        keyboard.append([InlineKeyboardButton(
            "─── 🎭 Мои личности ───",
            callback_data="pers:noop"
        )])

        for p in custom_personalities:
            button_text = f"🎨 {p.display_name}"
            if current_personality and p.name == current_personality:
                button_text += " ✓"

            callback_data = _build_callback_data(
                callback_prefix,
                p,
                user_id,
                extra_callback_data
            )

            # Build row based on context
            if context == "manage":
                # Management context: [Select] [✏️] [🗑️]
                keyboard.append([
                    InlineKeyboardButton(button_text, callback_data=callback_data),
                    InlineKeyboardButton("✏️", callback_data=f"pers:edit:{p.name}"),
                    InlineKeyboardButton("🗑️", callback_data=f"pers:delete:{p.name}")
                ])
            else:
                # Selection context: [Select only]
                keyboard.append([
                    InlineKeyboardButton(button_text, callback_data=callback_data)
                ])

    # 5. Create button
    if show_create_button:
        keyboard.append([InlineKeyboardButton(
            "➕ Создать свою личность",
            callback_data="pers:create_start"
        )])

    # 6. Back button
    if show_back_button:
        keyboard.append([InlineKeyboardButton(
            "◀️ Назад",
            callback_data=sign_callback_data(back_callback)
        )])

    return InlineKeyboardMarkup(keyboard)


def _build_callback_data(
    callback_prefix: str,
    personality,
    user_id: int,
    extra_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build callback_data string based on prefix and context.

    Args:
        callback_prefix: Prefix for callback (e.g., "pers:select", "summary_personality")
        personality: Personality object
        user_id: User ID for HMAC signature
        extra_data: Extra data to include (e.g., {"chat_id": 123, "limit": "50"})

    Returns:
        Formatted callback_data string

    Examples:
        # For /lichnost
        "pers:select:bydlan"

        # For /summary
        "summary_personality:123:5:none:signature"
    """
    # Handle different callback formats
    if callback_prefix.startswith("pers:"):
        # Simple format for /lichnost: "pers:select:name"
        return f"{callback_prefix}:{personality.name}"

    elif callback_prefix == "summary_personality":
        # Format: "summary_personality:<chat_id>:<personality_id>:<limit>:<signature>"
        chat_id = extra_data.get("chat_id") if extra_data else 0
        limit = extra_data.get("limit", "none") if extra_data else "none"

        callback_base = f"{chat_id}:{personality.id}:{limit}"
        signature = create_string_signature(callback_base, user_id)

        from config import logger
        logger.info(f"[SIGNATURE GEN] Creating callback for summary_personality: callback_base='{callback_base}', user_id={user_id}, signature={signature}, full='{callback_prefix}:{callback_base}:{signature}'")

        return f"{callback_prefix}:{callback_base}:{signature}"

    elif callback_prefix == "start_chat":
        # Format: "start_chat:personality_name" (for /chat command)
        # TODO: Add signature when /chat is implemented
        return f"{callback_prefix}:{personality.name}"

    elif callback_prefix == "judge_personality":
        # Format: "judge_personality:<chat_id>:<personality_id>:<signature>"
        chat_id = extra_data.get("chat_id") if extra_data else 0

        callback_base = f"{chat_id}:{personality.id}"
        signature = create_string_signature(callback_base, user_id)

        from config import logger
        logger.info(f"[JUDGE SIGNATURE GEN] Creating callback for judge_personality: callback_base='{callback_base}', user_id={user_id}, signature={signature}, full='{callback_prefix}:{callback_base}:{signature}'")

        return f"{callback_prefix}:{callback_base}:{signature}"

    else:
        # Default fallback
        return f"{callback_prefix}:{personality.name}"


def get_current_personality_display(user_id: int) -> str:
    """
    Get display name of user's current personality.

    Args:
        user_id: User ID

    Returns:
        Display name of current personality or "Нейтральный" as fallback
    """
    db = DBService()
    personality_name = db.get_user_personality(user_id)
    personality = db.get_personality(personality_name)

    if personality:
        return f"{personality.emoji} {personality.display_name}"
    else:
        return "🎓 Нейтральный"
