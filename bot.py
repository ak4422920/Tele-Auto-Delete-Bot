import os
import asyncio
from config import API_ID, API_HASH, BOT_TOKEN, DATABASE_URL, BOT_USERNAME, FORCE_SUB_CHANNEL, OWNER_ID

from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from flask import Flask, redirect
from threading import Thread
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram.errors import FloodWait

# MongoDB
client = AsyncIOMotorClient(DATABASE_URL)
db = client['databas']
groups = db['group_id']
users = db['users']

# Bot setup
bot = Client("deletebot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# ➤ Force Subscribe checker (only for admins)
async def check_force_sub(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(f"@{FORCE_SUB_CHANNEL}", user_id)
        if member.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.MEMBER]:
            return False
    except:
        return False
    return True


@bot.on_message(filters.command("start") & filters.private)
async def start(_, message):
    user_id = message.from_user.id

    if not await check_force_sub(bot, message.chat.id, user_id):
        btn = [[InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL}")]]
        await message.reply("**🔒 You must join our channel to use this bot!**", reply_markup=InlineKeyboardMarkup(btn))
        return

    await users.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)

    buttons = [
        [InlineKeyboardButton("🎈 Add Your Group", url=f"http://t.me/{BOT_USERNAME}?startgroup=none&admin=delete_messages")],
        [InlineKeyboardButton("❓ Help", callback_data="help"), InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ]
    await message.reply_text(
        "**👋 Welcome to Auto Deleter Bot!**\n\nI can auto-delete group messages after a set time.\nUse me in your groups to keep them clean.",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.MARKDOWN
    )


@bot.on_callback_query()
async def callback_handler(_, query: CallbackQuery):
    if query.data == "help":
        await query.message.edit_text(
            "**🛠 Help Menu**\n\n"
            "/set_time <sec> – Set auto delete timer.\n"
            "/disable – Disable auto-delete.\n"
            "/status – Show current delete timer.\n",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
        )
    elif query.data == "about":
        await query.message.edit_text(
            "**ℹ️ About**\n\n"
            "Auto Deleter Bot by @kissubots.\nMaintains group cleanliness by deleting messages after a time.\n",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
        )
    elif query.data == "back":
        await query.message.edit_text(
            "**👋 Welcome to Auto Deleter Bot!**\n\nI can auto-delete group messages after a set time.\nUse me in your groups to keep them clean.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎈 Add Your Group", url=f"http://t.me/{BOT_USERNAME}?startgroup=none&admin=delete_messages")],
                [InlineKeyboardButton("❓ Help", callback_data="help"), InlineKeyboardButton("ℹ️ About", callback_data="about")]
            ])
        )


@bot.on_message(filters.command("set_time"))
async def set_delete_time(_, message):
    if message.chat.type == enums.ChatType.PRIVATE:
        await message.reply("**Use this command in a group.**")
        return

    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        return await message.reply_text("**❌ Invalid usage. Example:** `/set_time 10`", parse_mode=enums.ParseMode.MARKDOWN)

    user_id = message.from_user.id
    async for m in bot.get_chat_members(message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
        if m.user.id == user_id:
            await groups.update_one({"group_id": message.chat.id}, {"$set": {"delete_time": args[1]}}, upsert=True)
            return await message.reply(f"✅ **Delete time set to {args[1]} seconds.**")
    await message.reply("❌ Only admins can set delete time.")


@bot.on_message(filters.command("status") & filters.group)
async def status(_, message):
    group = await groups.find_one({"group_id": message.chat.id})
    if group:
        await message.reply_text(f"**🕒 Current delete time:** `{group['delete_time']}` seconds")
    else:
        await message.reply_text("**🛑 Auto-delete is not set for this group.**")


@bot.on_message(filters.command("disable") & filters.group)
async def disable(_, message):
    user_id = message.from_user.id
    async for m in bot.get_chat_members(message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
        if m.user.id == user_id:
            await groups.delete_one({"group_id": message.chat.id})
            await message.reply_text("✅ **Auto-delete disabled for this group.**")
            return
    await message.reply("❌ Only admins can disable auto-delete.")


@bot.on_message(filters.command("broadcast") & filters.private)
async def broadcast(_, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ You're not authorized.")

    if len(message.command) < 2:
        return await message.reply("Usage: `/broadcast Your message here...`", parse_mode=enums.ParseMode.MARKDOWN)

    text = message.text.split(None, 1)[1]
    sent = 0
    failed = 0
    async for user in users.find({}):
        try:
            await bot.send_message(user["user_id"], text)
            sent += 1
            await asyncio.sleep(0.1)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except:
            failed += 1
            continue

    await message.reply(f"✅ Broadcast sent to {sent} users.\n❌ Failed: {failed}")


@bot.on_message(filters.command("users") & filters.private)
async def total_users(_, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ You're not authorized.")
    total = await users.count_documents({})
    await message.reply(f"👤 Total users: `{total}`", parse_mode=enums.ParseMode.MARKDOWN)


@bot.on_message(filters.group & filters.text)
async def auto_delete(_, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if message.from_user.is_bot:
        return

    group = await groups.find_one({"group_id": chat_id})
    if not group:
        return

    async for m in bot.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
        if m.user.id == user_id:
            return

    try:
        await asyncio.sleep(int(group["delete_time"]))
        await message.delete()
    except Exception as e:
        print(f"Error deleting message: {e}")


# Flask keep-alive
app = Flask(__name__)

@app.route('/')
def index():
    return redirect(f"https://t.me/{BOT_USERNAME}", code=302)

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 8080)))

if __name__ == "__main__":
    Thread(target=run).start()
    bot.run()
