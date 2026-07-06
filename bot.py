import asyncio
import os
import glob
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
    InputMediaPhoto,
    InputMediaVideo
)
from aiogram.filters import CommandStart
import yt_dlp

# قراءة التوكن من إعدادات البيئة (Render)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# معرف ورابط قناتك للاشتراك الإجباري
CHANNEL_USERNAME = "@your_channel"
CHANNEL_LINK = "https://t.me/your_channel"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# دالة التحقق من الاشتراك الإجباري في القناة
async def check_subscription(user_id: int):
    try:
        member = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user_id
        )
        return member.status in [
            "member",
            "administrator",
            "creator"
        ]
    except Exception:
        return False

# لوحة مفاتيح الاشتراك الإجباري باللغة العربية
def subscribe_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 اشترك في القناة لتفعيل البوت",
                    url=CHANNEL_LINK
                )
            ]
        ]
    )

# رسالة الترحيب /start باللغة العربية
@dp.message(CommandStart())
async def start(message: Message):
    if not await check_subscription(message.from_user.id):
        await message.answer(
            "عذراً، يجب عليك الاشتراك في القناة أولاً لاستخدام البوت المطور. 👇",
            reply_markup=subscribe_keyboard()
        )
        return

    await message.answer(
        "مرحباً بك! 👋\n"
        "أرسل لي الآن رابط فيديو أو صور من (TikTok , Instagram , Facebook , YouTube) "
        "وسأقوم بتحميل المحتوى لك بأعلى جودة وبدون علامة مائية تلقائياً. ⚡"
    )

# استقبال الروابط وتحميلها بشكل ذكي وشامل (فيديوهات وصور)
@dp.message(F.text.startswith(("http://", "https://")))
async def download(message: Message):
    user_id = message.from_user.id

    if not await check_subscription(user_id):
        await message.answer(
            "عذراً، يجب عليك الاشتراك في القناة أولاً لاستخدام البوت المطور. 👇",
            reply_markup=subscribe_keyboard()
        )
        return

    # رسالة الحالة أثناء المعالجة
    status = await message.answer(
        "⏳ جاري فحص الرابط ومعالجة المحتوى بدون علامة مائية، يرجى الانتظار..."
    )

    # إنشاء مجلد مؤقت فريد لكل مستخدم لمنع تداخل الملفات
    user_dir = f"downloads_{user_id}"
    os.makedirs(user_dir, exist_ok=True)

    try:
        url = message.text

        # إعدادات متطورة لـ yt-dlp لدعم الصور والفيديوهات وحماية الذاكرة العشوائية
        ydl_opts = {
            # حفظ الملفات بأسماء معرفة ومناسبة للامتدادات
            "outtmpl": f"{user_dir}/%(id)s_%(title)s.%(ext)s", 
            "quiet": True,
            "no_warnings": True,
            # اختيار أفضل جودة مدمجة مباشرة لتقليل استهلاك المعالج
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            # السماح بجلب امتدادات الصور المختلفة وألبومات التيك توك والانستا
            "allowed_extensions": ["mp4", "mkv", "mov", "webm", "jpg", "jpeg", "png", "webp"],
        }

        def run_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        # تشغيل التحميل في خيط منفصل (Executor) لضمان عدم توقف البوت أو تجمده
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            run_download
        )

        # جلب كافة الملفات التي تم تحميلها في مجلد المستخدم
        files = glob.glob(f"{user_dir}/*")

        if not files:
            await status.edit_text(
                "❌ عذراً، لم نتمكن من استخراج أو العثور على أي محتوى من هذا الرابط. تأكد من أن الحساب/المنشور عام."
            )
            return

        # تصنيف الملفات المكتشفة إلى صور وفيديوهات
        photos_list = []
        videos_list = []
        
        for file_path in files:
            if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                photos_list.append(file_path)
            elif file_path.lower().endswith((".mp4", ".mkv", ".mov", ".webm")):
                videos_list.append(file_path)

        # 1. إذا كان المحتوى المكتشف عبارة عن صور (ألبوم صور تيك توك أو إنستغرام)
        if photos_list and not videos_list:
            media_group = []
            # تليجرام يدعم إرسال 10 صور كحد أقصى في رسالة المجموعة الواحدة
            for i, photo in enumerate(photos_list[:10]):
                caption = "✅ تم تحميل ألبوم الصور بنجاح بدون علامة مائية." if i == 0 else ""
                media_group.append(InputMediaPhoto(media=FSInputFile(photo), caption=caption))
            
            await message.answer_media_group(media=media_group)
            await status.delete()

        # 2. إذا كان المحتوى المكتشف عبارة عن فيديو (أو عدة فيديوهات)
        elif videos_list:
            # إرسال الفيديو الأول المكتشف
            file_path = videos_list[0]
            await message.answer_video(
                video=FSInputFile(file_path),
                caption="✅ تم تحميل الفيديو بنجاح بأعلى جودة وبدون علامة مائية."
            )
            await status.delete()

        # 3. أي صيغ أخرى غير مباشرة يتم إرسالها كملف وثيقة
        else:
            file_path = files[0]
            await message.answer_document(
                document=FSInputFile(file_path),
                caption="✅ تم تحميل الملف."
            )
            await status.delete()

    except Exception as e:
        print(f"حدث خطأ أثناء التشغيل: {e}")
        await status.edit_text(
            "❌ حدث خطأ غير متوقع أثناء معالجة الرابط. يرجى التحقق من صحة الرابط والمحاولة مجدداً."
        )

    finally:
        # كود حماية السيرفر: تنظيف وحذف كافة الملفات والمجلدات المؤقتة فوراً مهما كانت النتيجة
        try:
            files = glob.glob(f"{user_dir}/*")
            for f in files:
                os.remove(f)

            if os.path.exists(user_dir):
                os.rmdir(user_dir)
        except Exception as cleanup_error:
            print(f"خطأ أثناء تنظيف الملفات: {cleanup_error}")


async def main():
    print("البوت المطور يعمل الآن باللغة العربية ودعم الصور والفيديوهات...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
