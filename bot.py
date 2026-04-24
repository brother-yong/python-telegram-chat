try:
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
except ImportError:
    pass

import os
import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_KEY"))
OWNER_ID = int(os.getenv("OWNER_ID", "450535522"))

ROLES = [
    ("💼", "The CFO"),
    ("📈", "The Growth Marketer"),
    ("🛒", "The Customer"),
    ("⚖️", "The Startup Lawyer"),
    ("😈", "The Devil's Advocate"),
    ("💀", "The Failed Founder"),
    ("🔥", "The Burned Investor"),
    ("😒", "The Cynical User"),
    ("⚙️", "The Ops Manager"),
    ("👔", "The Hiring Manager"),
    ("🧾", "The Accountant"),
    ("🏦", "The Acquirer"),
    ("🔭", "The Trend Spotter"),
    ("🐑", "The Copycat"),
    ("👨‍👩‍👧", "Your Parents"),
]

# Store per-user state
user_state = {}

def build_role_keyboard(selected: set) -> InlineKeyboardMarkup:
    buttons = []
    for emoji, name in ROLES:
        label = f"✅ {emoji} {name}" if name in selected else f"{emoji} {name}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"role:{name}")])
    buttons.append([InlineKeyboardButton("✅ Confirm Selection", callback_data="confirm")])
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    user_state[OWNER_ID] = {"step": "selecting", "roles": set()}
    await update.message.reply_text(
        "Welcome to AskMyBoard 🏛️\n\nSelect your board members below. Tap to toggle. Confirm when ready.",
        reply_markup=build_role_keyboard(set())
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        return
    await query.answer()

    state = user_state.get(OWNER_ID, {"step": "selecting", "roles": set()})

    if query.data.startswith("role:"):
        role = query.data[5:]
        if role in state["roles"]:
            state["roles"].remove(role)
        else:
            state["roles"].add(role)
        user_state[OWNER_ID] = state
        await query.edit_message_reply_markup(reply_markup=build_role_keyboard(state["roles"]))

    elif query.data == "confirm":
        if not state["roles"]:
            await query.answer("Select at least one role.", show_alert=True)
            return
        state["step"] = "waiting_for_idea"
        user_state[OWNER_ID] = state
        selected_list = "\n".join(f"• {r}" for r in state["roles"])
        await query.edit_message_text(
            f"Board confirmed:\n{selected_list}\n\nNow pitch your business idea."
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    state = user_state.get(OWNER_ID, {})
    if state.get("step") != "waiting_for_idea":
        await update.message.reply_text("Use /start to begin.")
        return
    await update.message.reply_text("🏛️ Your board is deliberating...")

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    user_state[OWNER_ID] = {"step": "selecting", "roles": set()}
    await update.message.reply_text(
        "Restarting. Select your board members.",
        reply_markup=build_role_keyboard(set())
    )

app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("restart", restart))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()