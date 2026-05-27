# bot.py - Ethiopian Shoe Store Bot (PostgreSQL/Supabase Backend)
import telebot
from telebot.storage import StateMemoryStorage
from config import BOT_TOKEN
from backend.handlers import register_handlers
from backend.admin import register_admin_handlers
from backend.orders import register_order_handlers
import time
import requests
from flask import Flask
from threading import Thread

print("🚀 Initializing Ethio Shoe Store Bot with PostgreSQL backend...")

# 1. ቦቱን ማዘጋጀት
state_storage = StateMemoryStorage()
bot = telebot.TeleBot(BOT_TOKEN, state_storage=state_storage)
bot.add_custom_filter(telebot.custom_filters.StateFilter(bot))

# 2. Register all handlers
register_admin_handlers(bot)
register_order_handlers(bot)
register_handlers(bot)

# 🌐 3. ለRender መሸወጃ የሚሆን የFlask ዌብ ሰርቨር መፍጠር
app = Flask('')

@app.route('/')
def home():
    return "Bot is Running Live!"

def run_flask():
    # Render በዲፎልት 10000 ፖርት ላይ ነው ዌብሳይት የሚፈልገው
    app.run(host='0.0.0.0', port=10000)

# ⏰ ቦቱ እንዳይተኛ ራሱን በየ 14 ደቂቃው የሚቀሰቅስ ፈንክሽን
def keep_alive():
    # ያንተ የቦት ሊንክ
    url = "https://my-shoe-store-bot-7k49.onrender.com" 
    
    time.sleep(30) # ሰርቨሩ መጀመሪያ ሙሉ በሙሉ እስኪነሳ ትንሽ ይጠብቅ
    while True:
        try:
            requests.get(url, timeout=10)
            print("⏰ ሰርቨሩ እንዳይተኛ ራሱን ቀስቅሷል (Pinged Successfully)!")
        except Exception as e:
            print(f"⚠️ Ping ስህተት ገጥሟል፦ {e}")
        
        time.sleep(14 * 60) # በየ 14 ደቂቃው (14 x 60 ሰከንድ) ይደጋገማል

# ቦቱን የማስነሻ ዋና ፈንክሽን
def run_bot():
    print("🚀 ቦቱ መነሳት ጀምሯል...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout, Exception) as e:
            print(f"⚠️ የኔትወርክ መቆራረጥ ገጥሟል፣ ከ 5 ሰከንድ በኋላ ይነሳል... [ስህተት፦ {e}]")
            time.sleep(5)
            continue

if __name__ == "__main__":
    # 1. የFlask ዌብ ሰርቨሩን ከበስተጀርባ ማስነሳት
    t1 = Thread(target=run_flask)
    t1.start()
    
    # 2. ራስን የመቀስቀሻውን ሎጂክ ከበስተጀርባ ማስነሳት
    t2 = Thread(target=keep_alive)
    t2.start()
    
    # 3. ቦቱን በዋናው መስመር ማስነሳት
    run_bot()