import os
import json
import html
import time
import requests
import threading
from flask import Flask
from waitress import serve
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# 1. Flask Web Server Setup
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "Bot is alive and running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    serve(web_app, host="0.0.0.0", port=port)

def self_ping():
    """Internal ping service to prevent thread idle drops."""
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not render_url:
        return
    
    time.sleep(15)  
    while True:
        try:
            requests.get(render_url, timeout=10)
        except Exception:
            pass
        time.sleep(600)  # Ping every 10 minutes

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "8847191622:AAHB_bxtk_XxlC9GoHvmw5RnvEg8jXCdc8s")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "1199886518")

# Your verified Google Sheet Web App URL
GOOGLE_SHEET_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxqQBM2ZI-Zu0_X3esVLD7knSQkrjGdwX41ZFZMuP75IJ8xRL7jOWbXWQKHpLqfM--XvQ/exec"

MAX_REGISTRATIONS = 40
COUNTER_FILE = "counter.json"

# Conversation States
LANGUAGE, NAME, GENDER, AGE, PHONE, EXPECTATION, PAYMENT = range(7)

# Text Localization
TEXTS = {
    'EN': {
        'welcome': "សូមស្វាគមន៍មកកាន់ មជ្ឈមណ្ឌលស្នេហា! សូមជ្រើសរើសភាសារបស់អ្នក៖\nWelcome to Sneha Centre! Please choose your preferred language:",
        'sold_out': "Sorry, this meditation session has reached its full capacity of 40 participants. Please stay tuned for our next event!",
        'ask_name': "Please enter your full name:",
        'ask_gender': "Please enter your gender:",
        'ask_age': "Please enter your age:",
        'ask_phone': "Please enter your phone number:",
        'ask_expectation': "What is your expectation for joining this session?",
        'payment_instructions': "Registration fee: <b>$5/person (Your donation will be used to support the well-being of individuals facing financial hardship.)</b>\n\nPlease pay via the QR code below.\n\n⚠️ <b>IMPORTANT:</b> Please send a <b>screenshot or photo of your payment receipt</b> here. We need this screenshot to confirm and process your registration!",
        'confirm_receipt': "Thank you! Sneha team will contact you shortly.\nFor more detail, please contact: @SnehaCentreCambodia",
        'voice_warning': "⚠️ Please send text messages only, voice notes are not supported. Please type your response:",
        'admin_notification': "🚨 <b>New Meditation Registration</b> (#{count}/40)\n\n"
                             "<b>Name:</b> {name}\n"
                             "<b>Gender:</b> {gender}\n"
                             "<b>Age:</b> {age}\n"
                             "<b>Phone:</b> {phone}\n"
                             "<b>Expectation:</b> {expectation}\n"
                             "<b>Telegram:</b> {tg_user}\n"
                             "<b>Language:</b> English"
    },
    'KM': {
        'sold_out': "សូមអភ័យទោស! វគ្គសមាធិនេះបានពេញចំនួនកំណត់ ៤០ នាក់ហើយ។ សូមរង់ចាំការចុះឈ្មោះសម្រាប់ព្រឹត្តិការណ៍បន្ទាប់!",
        'ask_name': "សូមបញ្ចូលឈ្មោះពេញរបស់អ្នក៖",
        'ask_gender': "សូមបញ្ចូលភេទរបស់អ្នក៖",
        'ask_age': "សូមបញ្ចូលអាយុរបស់អ្នក៖",
        'ask_phone': "សូមបញ្ចូលលេខទូរស័ព្ទរបស់អ្នក៖",
        'ask_expectation': "តើអ្នកមានការរំពឹងទុកអ្វីខ្លះក្នុងការចូលរួមវគ្គនេះ?",
        'payment_instructions': "តម្លៃចូលរួម: <b>៥ ដុល្លារ/ម្នាក់ (ការបរិច្ចាគនេះនឹងយកទៅប្រើប្រាស់ដើម្បីគាំទ្រសុខភាពផ្លូវចិត្តដល់អ្នកដែលខ្វះខាត)</b>\n\nសូមធ្វើការទូទាត់ប្រាក់តាមរយៈ QR code ខាងក្រោម។\n\n⚠️ <b>សំខាន់៖</b> សូមផ្ញើ <b>រូបថត ឬ Screenshot វិក្កយបត្រទូទាត់ប្រាក់</b> នៅទីនេះ។ យើងខ្ញុំត្រូវការរូបថតវិក្កយបត្រនេះ ដើម្បីផ្ទៀងផ្ទាត់ និងបញ្ជាក់ការចុះឈ្មោះរបស់អ្នក!",
        'confirm_receipt': "សូមអរគុណ! ក្រុមការងារ មជ្ឈមណ្ឌលស្នេហា នឹងទាក់ទងទៅអ្នកក្នុងពេលឆាប់ៗនេះ។\nសម្រាប់ព័ត៌មានបន្ថែម សូមទាក់ទង៖ @SnehaCentreCambodia",
        'voice_warning': "⚠️ សូមផ្ញើជាសារអក្សរ។ សូមវាយបញ្ចូលចម្លើយរបស់អ្នកម្ដងទៀត៖",
        'admin_notification': "🚨 <b>ការចុះឈ្មោះសមាធិថ្មី</b> (#{count}/40)\n\n"
                             "<b>ឈ្មោះ:</b> {name}\n"
                             "<b>ភេទ:</b> {gender}\n"
                             "<b>អាយុ:</b> {age}\n"
                             "<b>លេខទូរស័ព្ទ:</b> {phone}\n"
                             "<b>ការរំពឹងទុក:</b> {expectation}\n"
                             "<b>តេឡេក្រាម:</b> {tg_user}\n"
                             "<b>ភាសា:</b> ខ្មែរ"
    }
}

def get_counter():
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r") as f:
                data = json.load(f)
                return data.get("count", 0)
        except Exception:
            return 0
    return 0

def increment_counter():
    count = get_counter() + 1
    with open(COUNTER_FILE, "w") as f:
        json.dump({"count": count}, f)
    return count

def reset_counter_file():
    with open(COUNTER_FILE, "w") as f:
        json.dump({"count": 0}, f)

def save_to_google_sheet(user_data):
    """Pushes registration data matching columns B through F (Name, Gender, Age, Phone, Receipt)"""
    payload = {
        "name": user_data.get("name"),
        "gender": user_data.get("gender"),
        "age": user_data.get("age"),
        "phone": user_data.get("phone"),
        "receipt": user_data.get("receipt")
    }
    try:
        response = requests.post(GOOGLE_SHEET_WEB_APP_URL, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error saving to Google Sheet: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if get_counter() >= MAX_REGISTRATIONS:
        await update.message.reply_text(TEXTS['EN']['sold_out'])
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("ភាសាខ្មែរ 🇰🇭", callback_data='KM')],
        [InlineKeyboardButton("English 🇬🇧", callback_data='EN')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(TEXTS['EN']['welcome'], reply_markup=reply_markup)
    return LANGUAGE

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data
    context.user_data['lang'] = lang
    await query.edit_message_text(text=TEXTS[lang]['ask_name'])
    return NAME

async def handle_voice_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'KM')
    await update.message.reply_text(TEXTS[lang]['voice_warning'])

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = html.escape(update.message.text)
    lang = context.user_data['lang']
    await update.message.reply_text(TEXTS[lang]['ask_gender'])
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = html.escape(update.message.text)
    lang = context.user_data['lang']
    await update.message.reply_text(TEXTS[lang]['ask_age'])
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['age'] = html.escape(update.message.text)
    lang = context.user_data['lang']
    await update.message.reply_text(TEXTS[lang]['ask_phone'])
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = html.escape(update.message.text)
    lang = context.user_data['lang']
    await update.message.reply_text(TEXTS[lang]['ask_expectation'])
    return EXPECTATION

async def get_expectation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['expectation'] = html.escape(update.message.text)
    lang = context.user_data['lang']
    
    if os.path.exists('qr.jpg'):
        with open('qr.jpg', 'rb') as photo_file:
            await update.message.reply_photo(
                photo=photo_file,
                caption=TEXTS[lang]['payment_instructions'],
                parse_mode="HTML"
            )
    else:
        await update.message.reply_photo(
            photo="https://via.placeholder.com/300x300.png?text=Bakong+KHQR+Code",
            caption=TEXTS[lang]['payment_instructions'],
            parse_mode="HTML"
        )
    return PAYMENT

async def get_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_count = get_counter()
    lang = context.user_data['lang']
    if current_count >= MAX_REGISTRATIONS:
        await update.message.reply_text(TEXTS[lang]['sold_out'])
        return ConversationHandler.END

    photo = update.message.photo[-1]
    context.user_data['receipt'] = photo.file_id

    # Save to your Google Sheet matching your layout
    save_to_google_sheet(context.user_data)

    new_count = increment_counter()
    
    user = update.effective_user
    if user.username:
        tg_user = f"@{user.username}"
    else:
        tg_user = f'<a href="tg://user?id={user.id}">Contact User</a> (No @username)'

    await update.message.reply_text(TEXTS[lang]['confirm_receipt'])
    
    admin_text = TEXTS[lang]['admin_notification'].format(
        count=new_count,
        name=context.user_data['name'],
        age=context.user_data['age'],
        gender=context.user_data['gender'],
        phone=context.user_data['phone'],
        expectation=context.user_data['expectation'],
        tg_user=tg_user
    )
    
    await context.bot.send_photo(
        chat_id=ADMIN_CHAT_ID,
        photo=photo.file_id,
        caption=admin_text,
        parse_mode="HTML"
    )
    return ConversationHandler.END

async def reset_counter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_CHAT_ID):
        return
    reset_counter_file()
    await update.message.reply_text("🔄 Registration counter has been reset to 0 for the next event!")

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_CHAT_ID):
        return
    count = get_counter()
    await update.message.reply_text(f"📊 Current Registrations: {count}/40")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANGUAGE: [CallbackQueryHandler(set_language)],
            NAME: [
                MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_input),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)
            ],
            GENDER: [
                MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_input),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)
            ],
            AGE: [
                MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_input),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)
            ],
            PHONE: [
                MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_input),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)
            ],
            EXPECTATION: [
                MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_input),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_expectation)
            ],
            PAYMENT: [
                MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_input),
                MessageHandler(filters.PHOTO, get_payment)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("reset", reset_counter))
    app.add_handler(CommandHandler("status", check_status))

    print("Meditation Bot is running...")
    app.run_polling(stop_signals=None)

if __name__ == '__main__':
    main()
