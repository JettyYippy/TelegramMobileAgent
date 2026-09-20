import asyncio
import logging
import html
import time
from typing import Optional
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import config
from approval_manager import ApprovalManager
from agent_service import AgentService

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("TelegramMobileAgent")

# Initialize managers
approval_manager = ApprovalManager(timeout_seconds=300)
agent_service = AgentService(approval_manager=approval_manager)

def is_authorized(update: Update) -> bool:
    """Security check to ensure only the specified Telegram user can run commands."""
    user = update.effective_user
    if not user:
        return False
    if config.TELEGRAM_ALLOWED_USER_ID and user.id == config.TELEGRAM_ALLOWED_USER_ID:
        return True
    return False

async def unauthorized_warning(update: Update):
    """Replies with an access denied warning for unauthorized users."""
    if update.effective_message:
        await update.effective_message.reply_text(
            f"🚫 Access Denied.\nYour User ID (`{update.effective_user.id}`) is not authorized to control this desktop.",
            parse_mode=ParseMode.MARKDOWN
        )

def split_message(text: str, max_length: int = 4000) -> list[str]:
    """Splits long responses into chunks within Telegram's 4096 character limit."""
    chunks = []
    while len(text) > max_length:
        split_idx = text.rfind("\n", 0, max_length)
        if split_idx == -1:
            split_idx = max_length
        chunks.append(text[:split_idx])
        text = text[split_idx:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks

async def send_approval_card(action_id: str, tool_name: str, summary: str):
    """Callback used by ApprovalManager to send an interactive approval card to Telegram."""
    app = bot_app
    chat_id = config.TELEGRAM_ALLOWED_USER_ID
    if not chat_id or not app:
        return

    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{action_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject:{action_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"⚠️ **Action Requires Permission**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{summary}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"_Tap below to allow or deny this action on your computer._"
    )

    await app.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

agent_service.set_telegram_sender(send_approval_card)

# ----------------- Command Handlers -----------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_warning(update)

    user_first_name = update.effective_user.first_name if update.effective_user else "Developer"
    welcome_msg = (
        f"👋 **Welcome to TelegramMobileAgent!**\n\n"
        f"Connected to your computer as `{user_first_name}`.\n\n"
        f"📂 **Active Workspace:** `{agent_service.workspace_dir}`\n"
        f"⚡ **Review Mode:** `{agent_service.review_mode}` (Only destructive operations like `rm -rf` require your tap)\n\n"
        f"**Commands:**\n"
        f"• Send any natural prompt to start building or coding\n"
        f"• `/retry` - Re-runs your previous prompt\n"
        f"• `/status` - Check current agent activity and workspace\n"
        f"• `/workspace <path>` - View or switch workspace directory\n"
        f"• `/mode` - Switch between `high_risk`, `safe`, and `strict`\n"
        f"• `/reset` (or `/cancel`) - Reset agent state if stuck\n"
        f"• `/help` - Show command guide"
    )
    await update.message.reply_text(welcome_msg, parse_mode=ParseMode.MARKDOWN)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_warning(update)

    help_msg = (
        "🤖 **TelegramMobileAgent Guide**\n\n"
        "1. **Prompting**: Send any prompt to code, build, or manage tasks.\n"
        "2. **Commands (100% FREE - 0 Tokens Consumed)**:\n"
        "   • `/retry` - Re-runs your last prompt\n"
        "   • `/status` - Check agent state, active workspace, and review mode\n"
        "   • `/reset` (or `/cancel`) - Reset agent state if stuck\n"
        "   • `/workspace <path>` - View or switch active desktop folder\n"
        "   • `/mode [high_risk|safe|strict]` - Adjust approval sensitivity\n\n"
        "💡 _Note: Utility commands run locally on your machine for free! Only actual AI prompts consume API tokens._"
    )
    await update.message.reply_text(help_msg, parse_mode=ParseMode.MARKDOWN)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_warning(update)

    status_str = "🟢 Idle" if not agent_service.is_running else "🟡 Working on a task..."
    pending_count = len(approval_manager.pending_requests)

    msg = (
        f"📊 **Agent Status**\n\n"
        f"• **State:** {status_str}\n"
        f"• **Workspace:** `{agent_service.workspace_dir}`\n"
        f"• **Review Mode:** `{agent_service.review_mode}`\n"
        f"• **Pending Approvals:** {pending_count}\n"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def cmd_workspace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_warning(update)

    if not context.args:
        await update.message.reply_text(
            f"📂 Current workspace:\n`{agent_service.workspace_dir}`\n\nTo change, use:\n`/workspace /path/to/project`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    new_path = " ".join(context.args).strip('\'"')
    try:
        resolved = agent_service.set_workspace(new_path)
        await update.message.reply_text(
            f"✅ Workspace switched to:\n`{resolved}`",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error setting workspace: `{e}`", parse_mode=ParseMode.MARKDOWN)

async def cmd_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_warning(update)

    if context.args:
        target = context.args[0].lower()
        if target in ("high_risk", "high_risk_only", "risk", "default"):
            agent_service.set_review_mode("high_risk_only")
            await update.message.reply_text("⚡ Review mode set to **HIGH_RISK_ONLY** (only destructive commands halt for approval).", parse_mode=ParseMode.MARKDOWN)
        elif target in ("safe", "modifying"):
            agent_service.set_review_mode("safe")
            await update.message.reply_text("🛡️ Review mode set to **SAFE** (all file writes and commands require approval).", parse_mode=ParseMode.MARKDOWN)
        elif target in ("strict", "all"):
            agent_service.set_review_mode("strict")
            await update.message.reply_text("🔒 Review mode set to **STRICT** (all tools require approval).", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("Valid options: `/mode high_risk`, `/mode safe`, `/mode strict`", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(
            f"Current mode: **{agent_service.review_mode}**\n\n"
            "Options:\n"
            "• `/mode high_risk` - Only prompt for destructive commands like `rm -rf` (Recommended)\n"
            "• `/mode safe` - Prompt for all commands and file writes\n"
            "• `/mode strict` - Prompt for every tool",
            parse_mode=ParseMode.MARKDOWN
        )

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_warning(update)

    agent_service.is_running = False
    approval_manager.pending_requests.clear()
    await update.message.reply_text(
        "🔄 **Bridge Reset**: Agent state is now **Idle** and pending approvals have been cleared.",
        parse_mode=ParseMode.MARKDOWN
    )

# ----------------- Callback Query Handler (Button clicks) -----------------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_authorized(update):
        await query.answer("Unauthorized.", show_alert=True)
        return

    await query.answer()
    data = query.data or ""
    
    if ":" not in data:
        return

    action, action_id = data.split(":", 1)
    approved = (action == "approve")

    success, req = approval_manager.resolve(action_id, approved)
    if not success:
        await query.edit_message_text(
            f"⏱️ This request has already expired or been resolved.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    status_icon = "✅ Approved" if approved else "❌ Rejected"
    updated_text = (
        f"{status_icon} by you!\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{req.summary if req else 'Action resolved'}\n"
    )

    try:
        await query.edit_message_text(updated_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.warning("Could not update button message: %s", e)

# ----------------- Message & Prompt Handlers -----------------

last_user_prompt: str = ""

async def run_prompt_workflow(prompt: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executes prompt with live streaming updates to Telegram and error handling."""
    status_msg = await update.message.reply_text(
        "🧠 **Planning & preparing summary...**",
        parse_mode=ParseMode.MARKDOWN
    )

    async def on_thought(thought: str):
        logger.info("[Agent Thought] %s", thought)

    last_update_time = [0.0]
    accumulated_tokens = [""]

    async def on_token(token: str):
        accumulated_tokens[0] += token
        now = time.time()
        # Stream plan and response updates to Telegram live (throttled at ~1.3s to respect rate limits)
        if now - last_update_time[0] >= 1.3:
            last_update_time[0] = now
            preview = accumulated_tokens[0][:4000]
            try:
                await status_msg.edit_text(preview, parse_mode=ParseMode.MARKDOWN)
            except Exception:
                try:
                    await status_msg.edit_text(preview)
                except Exception:
                    pass

    try:
        response_text = await agent_service.execute_prompt(
            prompt=prompt,
            on_thought=on_thought,
            on_token=on_token
        )

        if not response_text.strip():
            response_text = "✅ Task processed. (No textual output returned by agent)."

        # Send final text / any remaining chunks
        chunks = split_message(response_text)
        for i, chunk in enumerate(chunks):
            if i == 0:
                try:
                    await status_msg.edit_text(chunk, parse_mode=ParseMode.MARKDOWN)
                except Exception:
                    await status_msg.edit_text(chunk)
            else:
                try:
                    await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
                except Exception:
                    await update.message.reply_text(chunk)

    except Exception as e:
        logger.exception("Error during prompt execution: %s", e)
        error_msg = f"❌ **Error executing task:**\n`{str(e)}`\n\n💡 _Tip: You can send `/retry` to re-run this prompt._"
        await update.message.reply_text(error_msg, parse_mode=ParseMode.MARKDOWN)

async def cmd_retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_warning(update)

    global last_user_prompt
    if not last_user_prompt:
        await update.message.reply_text("⚠️ No previous prompt found to retry.", parse_mode=ParseMode.MARKDOWN)
        return

    if agent_service.is_running:
        await update.message.reply_text(
            "⚠️ The agent is currently busy processing another task. Send `/reset` if it is stuck.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    preview = last_user_prompt[:160] + ("..." if len(last_user_prompt) > 160 else "")
    await update.message.reply_text(
        f"🔁 **Retrying previous prompt:**\n_{preview}_",
        parse_mode=ParseMode.MARKDOWN
    )
    await run_prompt_workflow(last_user_prompt, update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_warning(update)

    prompt = update.message.text
    if not prompt:
        return

    if agent_service.is_running:
        await update.message.reply_text(
            "⚠️ The agent is currently busy processing another task. Send `/reset` if it is stuck.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    global last_user_prompt
    last_user_prompt = prompt

    await run_prompt_workflow(prompt, update, context)

def main():
    errors = config.validate_config()
    if errors:
        print("Configuration errors detected:")
        for err in errors:
            print(f"  - {err}")
        print("\nPlease update .env file and restart.")
        return

    print("Starting TelegramMobileAgent...")
    print(f"Allowed User ID: {config.TELEGRAM_ALLOWED_USER_ID}")
    print(f"Default Workspace: {agent_service.workspace_dir}")

    global bot_app
    bot_app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("help", cmd_help))
    bot_app.add_handler(CommandHandler("status", cmd_status))
    bot_app.add_handler(CommandHandler("workspace", cmd_workspace))
    bot_app.add_handler(CommandHandler("mode", cmd_mode))
    bot_app.add_handler(CommandHandler("reset", cmd_reset))
    bot_app.add_handler(CommandHandler("cancel", cmd_reset))
    bot_app.add_handler(CommandHandler("retry", cmd_retry))
    bot_app.add_handler(CallbackQueryHandler(handle_callback))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is polling for messages. Press Ctrl+C to stop.")
    bot_app.run_polling()

if __name__ == "__main__":
    main()
