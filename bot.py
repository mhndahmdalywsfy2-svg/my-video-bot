import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest
import yt_dlp

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = "@ulxath"
CHANNEL_LINK = "https://t.me/ulxath"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def check_subscription(user_id: int):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except: return False

@dp.message(CommandStart())
async def start_cmd(message: Message):
    if await check_subscription(message.from_user.id):
        await message.answer("أهلاً بك! أرسل رابط الفيديو للتحميل.")
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="اشترك في القناة", url=CHANNEL_LINK)]])
        await message.answer("يجب الاشتراك في القناة أولاً:", reply_markup=kb)

@dp.message(F.text.startswith("http"))
async def download(message: Message):
    if not await check_subscription(message.from_user.id):
        return await message.answer("اشترك في القناة أولاً!")
    
    msg = await message.answer("جاري التحميل...")
    ydl_opts = {'outtmpl': 'video.mp4', 'format': 'best'}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([message.text])
        await message.answer_video(video=FSInputFile("video.mp4"))
        await msg.delete()
        os.remove("video.mp4")
    except:
        await msg.edit_text("حدث خطأ، تأكد من الرابط.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
