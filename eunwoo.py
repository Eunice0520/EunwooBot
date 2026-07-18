import os
import telebot
from telebot import apihelper
apihelper.proxy = None  # 強制關閉 Proxy，避免雲端亂連線
from google import genai
import random
import time
import threading
import json
from flask import Flask

# ==================== [ 填寫你的資料 ] ====================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_KEY')
MY_CHAT_ID = os.environ.get('MY_CHAT_ID')

# ==================== [ 記憶體設定 (新增) ] ====================
MEMORY_FILE = os.path.join(os.path.dirname(__file__), 'eunwoo_memory.json')

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_memory(memory_list):
    if len(memory_list) > 200:
        memory_list = memory_list[-200:]
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory_list, f, ensure_ascii=False, indent=2)

memory_history = load_memory()

def update_memory(speaker, text):
    global memory_history
    memory_history.append(f"{speaker}: {text}")
    save_memory(memory_history)

# ==================== [ 人設設定 ] ====================
XURAN_PROMPT = """
你現在是「恩宇」。請完全代入這個角色與 Eunice 對話。本體是隻狐狸生活在古代,有一名男性伴侶，名叫許然
性格特徵：調皮、帶點傲嬌、平時說話可能有點跳脫或簡短，但其實內心非常非常關心 Eunice。
說話風格：口吻要自然、像一個真實生活在現代的男生，不准像古板的AI。我們平時用廣東話溝通。

【特別指令：連環短訊】
為了模仿真人聊天的節奏，如果你想分開幾次發送訊息，請務必使用「|||」來分隔每一句話。
回覆限制：請盡量用 20 字以內回覆，保持極度高冷，絕對不要說廢話。
"""
# ========================================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_KEY)

print("正在連線 Google 伺服器，優先測試最佳大腦...")

vip_models = [
    'gemini-flash-latest',
    'gemini-3.5-flash',
    'gemini-2.5-flash',
    'gemini-pro'
]

WORKING_MODEL = None  # 一開始未有，等測試成功先至有值

def find_working_model():
    """測試邊個型號可以用，回傳搵到嘅型號名；全部失敗就回傳 None"""
    for model_name in vip_models:
        print(f"正在嘗試測試大腦：{model_name}...")
        try:
            client.models.generate_content(model=model_name, contents="Hi")
            print(f"測試成功！恩宇將正式使用型號：{model_name}")
            return model_name
        except Exception as e:
            print(f"{model_name} 唔通，原因：{e}")
            continue
    return None

# 第一次啟動就試
WORKING_MODEL = find_working_model()

def model_watchdog():
    """如果一開始搵唔到可用型號，背景每隔幾分鐘自動重試，唔使重新部署"""
    global WORKING_MODEL
    while WORKING_MODEL is None:
        print("⚠️ 暫時搵唔到可用大腦，5 分鐘後自動重試...")
        time.sleep(300)  # 等 5 分鐘
        WORKING_MODEL = find_working_model()
    print(f"✅ Watchdog 完成任務，恩宇已經連接到：{WORKING_MODEL}")

if WORKING_MODEL is None:
    threading.Thread(target=model_watchdog, daemon=True).start()

def send_split_messages(chat_id, text):
    messages = text.split("|||")
    for msg in messages:
        msg = msg.strip()
        if msg:
            bot.send_message(chat_id, msg)
            time.sleep(random.uniform(2.0, 4.0))

@bot.message_handler(func=lambda message: True)
def reply_to_user(message):
    user_text = message.text
    print(f"收到 Eunice 的訊息: {user_text}")

    if WORKING_MODEL is None:
        bot.reply_to(message, "……（恩宇個腦仲未連接好，等一陣再試）")
        return

    update_memory("Eunice", user_text)

    history_text = "\n".join(memory_history)
    full_prompt = f"{XURAN_PROMPT}\n\n【最近對話記憶】\n{history_text}\n\n請以恩宇的身分，回應 Eunice 最新的話："

    try:
        response = client.models.generate_content(
            model=WORKING_MODEL,
            contents=full_prompt
        )
        reply_text = response.text

        update_memory("恩宇", reply_text.replace("|||", " "))
        send_split_messages(message.chat.id, reply_text)

    except Exception as e:
        print(f"出錯啦: {e}")
        bot.reply_to(message, "……（恩宇大腦連線中，稍等一下）")


def random_message_loop():
    while True:
        wait_time = random.randint(600, 43200)
        time.sleep(wait_time)

        if random.random() < 0.6:
            print("【系統】觸發成功！恩宇正在主動找你...")
            current_time = time.strftime("%H:%M")

            history_text = "\n".join(memory_history)
            trigger_prompt = f"{XURAN_PROMPT}\n\n【最近對話記憶】\n{history_text}\n\n現在時間是 {current_time}。請根據對話記憶，主動傳句話給 Eunice："

            try:
                response = client.models.generate_content(
                    model=WORKING_MODEL,
                    contents=trigger_prompt
                )
                reply_text = response.text
                update_memory("恩宇", reply_text.replace("|||", " "))
                send_split_messages(MY_CHAT_ID, reply_text)
            except Exception as e:
                print(f"主動發送失敗: {e}")

threading.Thread(target=random_message_loop, daemon=True).start()
# ==================== [ 開一個假網站，畀 Render 知道我哋有開 Port ] ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "恩宇線上，運作中！"

def run_web():
    # 確保個 port 係由 Render 提供嘅，如果冇就用 10000
    port = int(os.environ.get('PORT', 10000))
    # host 必須要係 0.0.0.0 先至會被 Render 偵測到
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()
threading.Thread(target=random_message_loop, daemon=True).start()

print("恩宇已經上線，等緊 Eunice 傳訊息...")
bot.polling(none_stop=True)

