import telebot
from google import genai
import random
import time
import threading
import json
import os

# ==================== [ 填寫你的資料 ] ====================
TELEGRAM_TOKEN = '8847954122:AAFKjnD3f1SEAU9k6gGdmWc8xuqCWsOcbM4'  
GEMINI_KEY = 'AQ.Ab8RN6LVkyH02bzpPRj1T_6hdaDJ-NMFWbSNMExUYKQFSzeBmA'          # 請貼上你的 API Key
MY_CHAT_ID = 8024847200                    # 請填入你的 Chat ID

# ==================== [ 記憶體設定 (新增) ] ====================
MEMORY_FILE = '/Users/eunice/Desktop/eunwoo_memory.json'

# 讀取日記本
def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

# 寫入日記本
def save_memory(memory_list):
    # 將 40 改成 200，大約可以記住幾日到一個星期嘅內容
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

# 【大腦智能優先測試機制】(防超速 + 防失聯)
print("正在連線 Google 伺服器，優先測試最佳大腦...")

# 設立 VIP 優先名單 (由最新/最想用嘅排到最尾)
vip_models = [
    'gemini-flash-latest', 
    'gemini-1.5-flash', 
    'gemini-2.5-flash', 
    'gemini-pro'
]

WORKING_MODEL = 'gemini-pro' # 墊底預設

for model_name in vip_models:
    print(f"🔍 嘗試測試大腦：{model_name}...")
    try:
        # 只做極輕量測試，防止耗用太多資源
        client.models.generate_content(model=model_name, contents="Hi")
        WORKING_MODEL = model_name
        print(f"✅ 測試成功！恩宇將正式使用型號：{WORKING_MODEL}")
        break # 一旦成功就即刻跳出迴圈，絕對唔會超速！
    except Exception:
        print(f"❌ {model_name} 唔通，即刻試下一個...")
        continue
print(f"✅ 系統強制啟動：恩宇將正式使用型號：{WORKING_MODEL}")


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
        # 隨機休息時間：10分鐘 (600秒) 到 12個鐘 (43200秒)
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

print("🎉 恩宇終極版上線！(已配備寫日記長期記憶功能)")
bot.polling(none_stop=True)
