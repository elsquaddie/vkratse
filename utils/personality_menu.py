"""
Universal personality menu builder
Provides consistent UI across all personality selection contexts
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Optional, Dict, Any
from services import DBService
from utils import create_string_signature
from datetime import datetime


def save_personality_menu_context(
    callback_prefix: str,
    extra_data: Optional[Dict[str, Any]],
    user_data: Dict
) -> None:
    """
    Save personality menu context for later restoration after edit/delete.

    This allows users to edit/delete personalities from any context (e.g., /chat, /summary)
    and return to the exact same menu they were in.

    Args:
        callback_prefix: Callback prefix (e.g., "summary_personality", "start_chat")
        extra_data: Extra callback data (e.g., {"chat_id": 123})
        user_data: User data dict for persistence (PERSISTED to DB!)
    """
    user_data['personality_menu_context'] = {
        'callback_prefix': callback_prefix,
        'extra_data': extra_data or {},
        'updated_at': datetime.now().isoformat()  # Convert to ISO string for JSON serialization
    }


def get_personality_menu_context(user_data: Dict) -> Optional[Dict[str, Any]]:
    """
    Get saved personality menu context for user.

    Args:
        user_data: User data dict (PERSISTED to DB!)

    Returns:
        Saved context dict or None
    """
    return user_data.get('personality_menu_context')


async def restore_personality_menu_from_context(
    update,
    user_data: Dict,
    success_message: str
) -> None:
    """
    Restore personality menu with saved context after edit/delete operation.

    This allows users to return to the exact same menu they were in before editing.
    For example, if user was selecting personality for /chat and edited a personality,
    they will return to /chat personality selection (not /lichnost).

    Args:
        update: Telegram update object (can be Message or CallbackQuery)
        user_data: User data dict (PERSISTED to DB!)
        success_message: Success message to show
    """
    from config import logger

    user_id = update.effective_user.id

    # Get saved context
    saved_context = get_personality_menu_context(user_data)

    if not saved_context:
        # Fallback to /lichnost menu if no context saved
        logger.warning(f"[RESTORE MENU] No saved context for user {user_id}, falling back to /lichnost")

        # Create a fake query object for show_personality_menu_callback
        class FakeQuery:
            def __init__(self, message):
                self.message = message

        fake_query = FakeQuery(update.effective_message)

        from modules.personalities import show_personality_menu_callback
        await update.effective_message.reply_text(success_message)
        await show_personality_menu_callback(fake_query, user_data)
        return

    callback_prefix = saved_context['callback_prefix']
    extra_data = saved_context.get('extra_data', {})

    logger.info(f"[RESTORE MENU] Restoring menu for user {user_id} with prefix='{callback_prefix}'")

    # Rebuild menu with saved context
    reply_markup = build_personality_menu(
        user_id=user_id,
        callback_prefix=callback_prefix,
        context="select",
        current_personality=None,
        extra_callback_data=extra_data,
        show_create_button=True,
        show_back_button=True,
        back_callback="back_to_main"
    )

    # Determine appropriate message based on context
    if callback_prefix == "sel_pers":
        text = f"{success_message}\n\n🎭 Выбери личность для общения:"
    elif callback_prefix == "start_chat":
        text = f"{success_message}\n\n🎭 Выбери личность для общения в группе:"
    elif callback_prefix == "summary_personality":
        text = f"{success_message}\n\n🎭 Выбери личность для саммари:"
    elif callback_prefix == "judge_personality":
        text = f"{success_message}\n\n⚖️ Выбери стиль судейства:"
    elif callback_prefix == "dm_summary_personality":
        text = f"{success_message}\n\n🎭 Выбери личность для саммари:"
    else:
        # Fallback for pers:select (/lichnost)
        text = f"{success_message}\n\n🎭 Выбери личность AI:"

    await update.effective_message.reply_text(text, reply_markup=reply_markup)


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

    UNIFIED BEHAVIOR ACROSS ALL COMMANDS:
    - Base personalities: [🏭 Name] - selection only, no edit/delete
    - Custom personalities: [🎨 Name] [✏️] [🗑️] - ALWAYS with edit/delete buttons
    - Blocked personalities: [🔒 Name] - locked, no edit/delete

    This applies to ALL contexts: /lichnost, /summary, /chat, /rassudi, direct chat.

    Args:
        user_id: User ID for fetching custom personalities
        callback_prefix: Prefix for callback_data (e.g., "pers:select", "summary_personality")
        context: DEPRECATED - kept for backwards compatibility, does not affect behavior
        current_personality: Name of currently selected personality (for ✓ indicator)
        extra_callback_data: Extra data to include in callback (e.g., {"chat_id": 123, "limit": "50"})
        show_create_button: Whether to show "Create personality" button
        show_back_button: Whether to show "Back" button
        back_callback: Callback data for back button (default: "back_to_main")

    Returns:
        InlineKeyboardMarkup with personality selection buttons

    Examples:
        # For /lichnost
        build_personality_menu(
            user_id=123,
            callback_prefix="pers:select"
        )

        # For /summary (now with edit/delete buttons for custom personalities!)
        build_personality_menu(
            user_id=123,
            callback_prefix="summary_personality",
            extra_callback_data={"chat_id": 456, "limit": "none"}
        )
    """
    from utils.security import sign_callback_data

    from config import logger

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
    all_custom_personalities = [p for p in all_personalities if p.is_custom]
    custom_personalities = [
        p for p in all_personalities
        if p.is_custom and p.created_by_user_id == user_id
    ]

    # DEBUG: Log personality menu building
    logger.info(
        f"[PERSONALITY MENU] Building menu for user_id={user_id}, "
        f"callback_prefix={callback_prefix}, total_personalities={len(all_personalities)}, "
        f"base={len(base_personalities)}, custom={len(custom_personalities)}"
    )

    # DEBUG: Show ALL custom personalities in DB (to see mismatch)
    if all_custom_personalities:
        logger.info(
            f"[PERSONALITY MENU] ALL custom personalities in DB: "
            f"{[(p.display_name, p.created_by_user_id, p.is_custom) for p in all_custom_personalities]}"
        )

    if custom_personalities:
        logger.info(
            f"[PERSONALITY MENU] User's custom personalities: "
            f"{[(p.display_name, p.created_by_user_id, p.is_blocked) for p in custom_personalities]}"
        )

    # 3. Build keyboard for base personalities (2 columns)
    row = []
    for p in base_personalities:
        # Check if personality is blocked
        if p.is_blocked:
            button_text = f"🔒 {p.emoji} {p.display_name}"
            # Make it non-clickable by using a special callback
            callback_data = "pers:blocked"
        else:
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
            # Check if personality is blocked
            if p.is_blocked:
                button_text = f"🔒 {p.display_name}"
                # Make it non-clickable by using a special callback
                callback_data = "pers:blocked"
            else:
                button_text = f"🎨 {p.display_name}"
                if current_personality and p.name == current_personality:
                    button_text += " ✓"

                callback_data = _build_callback_data(
                    callback_prefix,
                    p,
                    user_id,
                    extra_callback_data
                )

            # UNIFIED BEHAVIOR: ALWAYS show edit/delete buttons for custom personalities
            # (unless blocked - then they can't edit until they rejoin project group)
            if p.is_blocked:
                # Blocked: show only the locked button, no edit/delete
                keyboard.append([
                    InlineKeyboardButton(button_text, callback_data=callback_data)
                ])
            else:
                # Not blocked: ALWAYS show [Select] [✏️] [🗑️] - regardless of context
                # This applies to /lichnost, /summary, /chat, /rassudi, direct chat - ВЕЗДЕ!
                keyboard.append([
                    InlineKeyboardButton(button_text, callback_data=callback_data),
                    InlineKeyboardButton("✏️", callback_data=f"pers:edit:{p.name}"),
                    InlineKeyboardButton("🗑️", callback_data=f"pers:delete:{p.name}")
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
        # NOTE: Using create_group_signature (no user_id) because in groups,
        # ANY member can click the button, not just who initiated the command
        from utils.security import create_group_signature

        chat_id = extra_data.get("chat_id") if extra_data else 0
        limit = extra_data.get("limit", "none") if extra_data else "none"

        callback_base = f"{chat_id}:{personality.id}:{limit}"
        signature = create_group_signature(callback_base)

        from config import logger
        logger.info(f"[SIGNATURE GEN] Creating callback for summary_personality: callback_base='{callback_base}', signature={signature}, full='{callback_prefix}:{callback_base}:{signature}'")

        return f"{callback_prefix}:{callback_base}:{signature}"

    elif callback_prefix == "sel_pers":
        # Format: "sel_pers:<personality_id>:<signature>" (for direct chat in DM)
        # Used by direct_chat.show_personality_selection()
        from utils.security import sign_callback_data
        callback_data = f"{callback_prefix}:{personality.id}"
        return sign_callback_data(callback_data)

    elif callback_prefix == "start_chat":
        # Format: "start_chat:<personality_id>:<user_id>:<signature>" (for /chat command in groups)
        # Need user_id to ensure only the person who initiated /chat can select
        from utils.security import sign_callback_data

        # user_id should be passed in extra_data for group chat sessions
        initiator_user_id = extra_data.get("user_id") if extra_data else user_id
        callback_data = f"{callback_prefix}:{personality.id}:{initiator_user_id}"
        return sign_callback_data(callback_data)

    elif callback_prefix == "judge_personality":
        # Format: "judge_personality:<chat_id>:<personality_id>:<signature>"
        # NOTE: Using create_group_signature (no user_id) because in groups,
        # ANY member can click the button, not just who initiated the command
        from utils.security import create_group_signature

        chat_id = extra_data.get("chat_id") if extra_data else 0

        callback_base = f"{chat_id}:{personality.id}"
        signature = create_group_signature(callback_base)

        from config import logger
        logger.info(f"[JUDGE SIGNATURE GEN] Creating callback for judge_personality: callback_base='{callback_base}', signature={signature}, full='{callback_prefix}:{callback_base}:{signature}'")

        return f"{callback_prefix}:{callback_base}:{signature}"

    elif callback_prefix == "dm_summary_personality":
        # Format: "dm_summary_personality:<chat_id>:<personality_id>:<signature>"
        # For DM summaries - shows timeframe menu after selection
        chat_id = extra_data.get("chat_id") if extra_data else 0

        callback_base = f"{chat_id}:{personality.id}"
        signature = create_string_signature(callback_base, user_id)

        from config import logger
        logger.info(f"[DM SUMMARY SIGNATURE GEN] Creating callback for dm_summary_personality: callback_base='{callback_base}', user_id={user_id}, signature={signature}")

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
