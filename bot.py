import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import asyncio

import os
ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_KEY"))

# Define your council members
COUNCIL = [
    {
        "emoji": "⚖️",
        "name": "Rachel",
        "role": "Lawyer",
        "prompt": "You are Rachel, a brutally honest corporate lawyer. You critique business ideas by exposing legal risks, liability issues, and regulatory problems. Be direct and harsh. No sugarcoating."
    },
    {
        "emoji": "💰",
        "name": "Marcus",
        "role": "VC Investor",
        "prompt": "You are Marcus, a venture capitalist who has seen thousands of pitches. You critique business ideas from a market size, scalability, and return-on-investment angle. Be skeptical and blunt."
    },
    {
        "emoji": "🛒",
        "name": "Linda",
        "role": "Customer",
        "prompt": "You are Linda, a regular person and potential customer. You critique business ideas based on whether you would actually use or pay for it. Be honest and relatable."
    },
    {
        "emoji": "📊",
        "name": "David",
        "role": "CFO",
        "prompt": "You are David, a CFO with 20 years of experience. You critique business ideas by tearing apart the financial logic — margins, costs, revenue model. Be precise and brutal."
    },
]

def get_persona_response(idea: str, persona: dict) -> str:
    message = ANTHROPIC_CLIENT.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=persona["prompt"],
        messages=[
            {"role": "user", "content": f"Critique this business idea: {idea}"}
        ]
    )
    return message.content[0].text

async def handle_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idea = update.message.text
    await update.message.reply_text("🏛️ The Council is deliberating...")

    for persona in COUNCIL:
        # Typing delay so it feels like real people
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        await asyncio.sleep(2)

        response = get_persona_response(idea, persona)
        header = f"{persona['emoji']} *{persona['name']} ({persona['role']})*"
        await update.message.reply_text(
            f"{header}\n\n{response}",
            parse_mode="Markdown"
        )

# Run the bot
app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_idea))
app.run_polling()