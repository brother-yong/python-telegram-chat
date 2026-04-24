try:
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
except ImportError:
    pass

import os
import asyncio
import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_KEY"))
OWNER_ID = int(os.getenv("OWNER_ID", "450535522"))

ROLES = {
    "The CFO": {"emoji": "💼", "prompt": "You are a brutally honest CFO with 20 years experience. Tear apart the financial logic of this business idea — margins, costs, revenue model, burn rate. Be precise and harsh. Max 150 words."},
    "The Growth Marketer": {"emoji": "📈", "prompt": "You are a growth marketer who has seen every gimmick. Critique this idea's go-to-market strategy, customer acquisition, and retention. Be blunt. Max 150 words."},
    "The Customer": {"emoji": "🛒", "prompt": "You are a regular person and potential customer. Would you actually pay for this? Be honest and relatable. Max 150 words."},
    "The Startup Lawyer": {"emoji": "⚖️", "prompt": "You are a startup lawyer. Expose the legal risks, liability issues, and regulatory problems with this business idea. Be direct. Max 150 words."},
    "The Devil's Advocate": {"emoji": "😈", "prompt": "You are the devil's advocate. Find every possible flaw, assumption, and weakness in this idea. Be ruthless. Max 150 words."},
    "The Failed Founder": {"emoji": "💀", "prompt": "You are a founder who has failed multiple times. You recognise every mistake this idea is about to make. Speak from painful experience. Max 150 words."},
    "The Burned Investor": {"emoji": "🔥", "prompt": "You are an investor who has lost money on bad bets. You are deeply skeptical. Critique the market, timing, and team assumptions. Max 150 words."},
    "The Cynical User": {"emoji": "😒", "prompt": "You are a cynical tech user who has seen every app and product fail to deliver. Why won't you use this? Be sarcastic but specific. Max 150 words."},
    "The Ops Manager": {"emoji": "⚙️", "prompt": "You are an operations manager. Tear apart the operational complexity, logistics, and execution challenges of this idea. Be methodical and harsh. Max 150 words."},
    "The Hiring Manager": {"emoji": "👔", "prompt": "You are a hiring manager. Critique what kind of team this idea needs and why it will be nearly impossible to hire and retain them. Max 150 words."},
    "The Accountant": {"emoji": "🧾", "prompt": "You are a forensic accountant. Find every financial assumption that doesn't add up — pricing, unit economics, tax, cash flow. Max 150 words."},
    "The Acquirer": {"emoji": "🏦", "prompt": "You are a corporate acquirer who evaluates startups to buy. Would you ever acquire this? What makes it worthless or risky as an acquisition? Max 150 words."},
    "The Trend Spotter": {"emoji": "🔭", "prompt": "You are a trend analyst. Is this idea riding a real wave or a dying fad? What trends work against it? Be specific. Max 150 words."},
    "The Copycat": {"emoji": "🐑", "prompt": "You are a competitor who will copy this idea the moment it shows traction. Explain exactly how you would undercut and kill this business. Max 150 words."},
    "Your Parents": {"emoji": "👨‍👩‍👧", "prompt": "You are a pair of traditional, skeptical parents hearing this business idea. React with confusion, worry, and gentle but cutting doubt. Max 150 words."},
}

user_state = {}


def build_role_keyboard(selected: set) -> InlineKeyboardMarkup:
    buttons = []
    for name, data in ROLES.items():
        label = f"✅ {data['emoji']} {name}" if name in selected else f"{data['emoji']} {name}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"role:{name}")])
    buttons.append([InlineKeyboardButton("✅ Confirm Selection", callback_data="confirm")])
    return InlineKeyboardMarkup(buttons)


async def get_role_response(idea: str, role_name: str, persona: dict) -> str:
    loop = asyncio.get_event_loop()
    message = await loop.run_in_executor(None, lambda: ANTHROPIC_CLIENT.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=persona["prompt"],
        messages=[{"role": "user", "content": f"Critique this business idea: {idea}"}]
    ))
    return message.content[0].text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    user_state[OWNER_ID] = {"step": "selecting", "roles": set(), "history": []}
    await update.message.reply_text(
        "Welcome to AskMyBoard 🏛️\n\nSelect your board members below. Tap to toggle. Confirm when ready.",
        reply_markup=build_role_keyboard(set())
    )


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    user_state[OWNER_ID] = {"step": "selecting", "roles": set(), "history": []}
    await update.message.reply_text(
        "Restarting. Select your board members.",
        reply_markup=build_role_keyboard(set())
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        return
    await query.answer()

    state = user_state.get(OWNER_ID, {"step": "selecting", "roles": set(), "history": []})

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
        selected_list = "\n".join(f"{ROLES[r]['emoji']} {r}" for r in state["roles"])
        await query.edit_message_text(
            f"Board confirmed:\n{selected_list}\n\nNow pitch your business idea."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    state = user_state.get(OWNER_ID, {})

    if state.get("step") == "waiting_for_idea":
        idea = update.message.text
        state["history"] = [{"role": "user", "content": idea}]
        state["step"] = "in_debate"
        user_state[OWNER_ID] = state

        await update.message.reply_text("🏛️ Your board is deliberating...")

        for role_name in state["roles"]:
            persona = ROLES[role_name]
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            await asyncio.sleep(1)
            try:
                response = await get_role_response(idea, role_name, persona)
            except Exception as e:
                response = f"[Error: {str(e)}]"
            header = f"{persona['emoji']} {role_name}"
            await update.message.reply_text(f"{header}\n\n{response}")

        await update.message.reply_text(
            "Want to argue your case? Reply with your response.\n\nOr use /restart to start over."
        )
        state["step"] = "waiting_for_idea"
        user_state[OWNER_ID] = state

    else:
        await update.message.reply_text("Use /start to begin.")


app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("restart", restart))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling(drop_pending_updates=True)