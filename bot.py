import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest
import yt_dlp

# قراءة التوكن من إعدادات Render
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = "@ulxath"
CHANNEL_LINK = "https://t.me/ulxath"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# دالة التحقق من الاشتراك الإجباري
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Subscription check error: {e}")
        return False

# لوحة مفاتيح الاشتراك الإجباري
def get_subscribe_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔔 اشترك في القناة أولاً", url=CHANNEL_LINK)]
    ])

# الاستجابة لأمر /start
@dp.message(CommandStart())
async def start_cmd(message: Message):
    try:
        is_subscribed = await check_subscription(message.from_user.id)
        if is_subscribed:
            await message.answer("أهلاً بك! 👋\nأرسل لي رابط فيديو من منصات التواصل وسأقوم بتحميله بدون علامة مائية.")
        else:
            await message.answer(
                "عذراً، يجب عليك الاشتراك في القناة المخصصة أولاً لاستخدام البوت.",
                reply_markup=get_subscribe_keyboard()
            )
    except Exception as e:
        print(f"Start command error: {e}")

# الاستجابة للروابط والتحميل الآمن
@dp.message(F.text.regexp(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'))
async def download_video(message: Message):
    user_id = message.from_user.id
    
    # التحقق من الاشتراك قبل البدء
    if not await check_subscription(user_id):
        await message.answer(
            "عذراً، يجب عليك الاشتراك في القناة المخصصة أولاً لاستخدام البوت.",
            reply_markup=get_subscribe_keyboard()
        )
        return

    url = message.text
    status_msg = await message.answer("⏳ جاري معالجة الرابط وتحميل الفيديو، يرجى الانتظار...")

    # اسم ملف فريد لكل مستخدم لتجنب التداخل وضياع الملفات
    output_filename = f"video_{user_id}.mp4"
    
    # إعدادات متوازنة لـ yt-dlp لحماية الذاكرة (RAM) في السيرفر المجاني
    ydl_opts = {
        'format': 'best[ext=mp4]/best', # اختيار صيغة MP4 مباشرة لتقليل استهلاك المعالج في الدمج
        'outtmpl': output_filename,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        # تشغيل التحميل بشكل منفصل لتجنب تعليق البوت
        loop = asyncio.get_event_loop()
        def run_dl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        
        await loop.run_in_executor(None, run_dl)

        # التأكد من أن الملف تم تحميله بنجاح قبل إرساله
        if os.path.exists(output_filename):
            video_file = FSInputFile(output_filename)
            await message.answer_video(video=video_file, caption="✅ تم التحميل بنجاح!\n@ulxath")
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ لم نتمكن من العثور على ملف الفيديو، قد يكون الرابط غير مدعوم.")

    except Exception as e:
        print(f"Download error: {e}")
        await status_msg.edit_text("❌ حدث خطأ غير متوقع أثناء معالجة هذا الرابط. تأكد من أنه عام وصحيح.")
    
    finally:
        # كود حرج: تنظيف السيرفر وحذف الملف فوراً مهما حدث (سواء نجح التحميل أو فشل)
        if os.path.exists(output_filename):
            try:
                os.remove(output_filename)
            except Exception as e:
                print(f"File removal error: {e}")

# تشغيل البوت
async def main():
    print("Bot is running securely...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
