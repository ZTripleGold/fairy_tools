import os
import time
import requests
import json
import uuid
import httpx
from playsound import playsound
from cozepy import COZE_CN_BASE_URL, Coze, TokenAuth, Message, ChatEventType, SyncHTTPClient

# ================================== 核心参数 ==================================
coze_api_token = 'pat_LvajxnygGTAcnNCkRuWsY9rOXFssP2w6P04mjXPHHdud56kMtzeazhFUC8ZmqQES'
coze_api_base = COZE_CN_BASE_URL
bot_id = '7607805028379901978'
user_id = 'TripleG_Live'

GPT_SOVITS_API = "http://127.0.0.1:9880"
REFER_WAV_PATH = r"E:\liveTools\GPT-SoVITS-v2pro-20250604-nvidia50\GPT-SoVITS-v2pro-20250604-nvidia50\Voice\Fairy\Ref\1.wav"
PROMPT_TEXT = "主人，我注意到您的数据在近期进行过一起，由第三方参与的销毁与转移。"
PROMPT_LANGUAGE = "zh"
TEXT_LANGUAGE = "zh"

LOG_FILE_PATH = r"E:\liveTools\BarrageGrab\logs\弹幕日志\(58409059349)TripleG（崩绝双修）\2026年02月19日直播\场次7608550282783623976\弹幕消息.txt"
ALLOW_KEYWORDS = ["配队", "机制", "怎么打", "翻车", "BOSS", "危局", "防卫战", "Fairy", "绳匠"]
MAX_REPLY_LENGTH = 300
# ========================================================================================

# 初始化Coze客户端（超长超时）
http_client = SyncHTTPClient(timeout=httpx.Timeout(
    timeout=120.0,
    connect=10.0
))

coze = Coze(
    auth=TokenAuth(token=coze_api_token),
    base_url=coze_api_base,
    http_client=http_client
)

processing_count = [0]

# ================================== GPT-SoVITS API调用函数（重点优化删除逻辑） ==================================
def tts_and_play(text):
    processing_count[0] += 1
    temp_audio_path = f"temp_fairy_{uuid.uuid4().hex[:8]}.wav"
    play_success = False  # 标记是否播放成功
    
    try:
        # 1. 调用GPT-SoVITS生成音频
        request_body = {
            "refer_wav_path": REFER_WAV_PATH,
            "prompt_text": PROMPT_TEXT,
            "prompt_language": PROMPT_LANGUAGE,
            "text": text,
            "text_language": TEXT_LANGUAGE
        }
        
        response = requests.post(GPT_SOVITS_API, json=request_body, timeout=120)
        if response.status_code != 200:
            print(f"❌ API返回错误，状态码：{response.status_code}")
            return
        
        # 2. 保存音频文件
        with open(temp_audio_path, "wb") as audio_file:
            audio_file.write(response.content)
        
        # 3. 播放音频（阻塞执行，直到播放完成）
        playsound(temp_audio_path)
        print(f"✅ Fairy语音播放完成：{text}")
        play_success = True

    except requests.exceptions.Timeout:
        print("❌ API请求超时，建议缩短回复文本长度")
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到GPT-SoVITS API，请检查服务是否启动")
    except Exception as e:
        print(f"❌ 语音合成/播放失败：{e}")
    finally:
        processing_count[0] -= 1
        
        # 4. 核心优化：无论播放成功/失败，都强制删除文件（多重重试）
        if os.path.exists(temp_audio_path):
            # 最多重试5次，每次间隔0.5秒（解决文件被占用的问题）
            for retry in range(5):
                try:
                    # 先解除文件占用（Windows特有）
                    if os.name == 'nt':  # 判断是否为Windows系统
                        import ctypes
                        ctypes.windll.kernel32.DeleteFileW(temp_audio_path)
                    else:
                        os.remove(temp_audio_path)
                    
                    if not os.path.exists(temp_audio_path):
                        print(f"🗑️ 临时音频文件已删除：{temp_audio_path}")
                        break
                except PermissionError:
                    print(f"⚠️ 文件被占用，重试删除（{retry+1}/5）...")
                    time.sleep(0.5)
                except Exception as e:
                    print(f"⚠️ 删除文件失败：{e}")
                    time.sleep(0.5)
            
            # 最终检查：如果还没删除，给出警告
            if os.path.exists(temp_audio_path):
                print(f"❌ 多次重试仍无法删除文件：{temp_audio_path}")

# ================================== Coze智能体调用函数 ==================================
def get_fairy_reply(danmu_text):
    try:
        reply_content = ""
        for event in coze.chat.stream(
            bot_id=bot_id,
            user_id=user_id,
            additional_messages=[
                Message.build_user_question_text(danmu_text),
            ],
        ):
            if event.event == ChatEventType.CONVERSATION_MESSAGE_DELTA:
                reply_content += event.message.content
            if event.event == ChatEventType.CONVERSATION_CHAT_COMPLETED:
                print(f"📊 Coze Token消耗：{event.chat.usage.token_count}")
        
        if len(reply_content) > MAX_REPLY_LENGTH:
            reply_content = reply_content[:MAX_REPLY_LENGTH]
        return reply_content.strip()
    except Exception as e:
        print(f"❌ Coze调用失败：{e}")
        return None

# ================================== 弹幕日志实时监控函数 ==================================
def monitor_danmu_log():
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            f.seek(0, 2)
            print("="*60)
            print("🎮 绝区零Fairy直播助手已启动（文件自动删除版）")
            print(f"📂 监控日志：{LOG_FILE_PATH}")
            print(f"🔍 回复关键词：{ALLOW_KEYWORDS}")
            print("="*60)
            
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                
                danmu_raw = line.strip()
                if ":" in danmu_raw:
                    danmu_text = danmu_raw.split(":", 1)[1].strip()
                else:
                    danmu_text = danmu_raw
                
                if not danmu_text or len(danmu_text) < 2:
                    continue
                if not any(keyword in danmu_text for keyword in ALLOW_KEYWORDS):
                    continue
                if processing_count[0] >= 2:
                    continue
                
                print(f"\n💬 收到弹幕：{danmu_text}")
                fairy_reply = get_fairy_reply(danmu_text)
                if not fairy_reply:
                    continue
                print(f"🧚 Fairy回复：{fairy_reply}")
                tts_and_play(fairy_reply)

    except UnicodeDecodeError:
        print("⚠️ UTF-8编码失败，自动切换GBK编码...")
        with open(LOG_FILE_PATH, "r", encoding="gbk") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                danmu_raw = line.strip()
                if ":" in danmu_raw:
                    danmu_text = danmu_raw.split(":", 1)[1].strip()
                else:
                    danmu_text = danmu_raw
                if not danmu_text or len(danmu_text) < 2:
                    continue
                if not any(keyword in danmu_text for keyword in ALLOW_KEYWORDS):
                    continue
                if processing_count[0] >= 2:
                    continue
                print(f"\n💬 收到弹幕：{danmu_text}")
                fairy_reply = get_fairy_reply(danmu_text)
                if fairy_reply:
                    print(f"🧚 Fairy回复：{fairy_reply}")
                    tts_and_play(fairy_reply)
    except FileNotFoundError:
        print(f"❌ 错误：找不到日志文件，请检查路径：{LOG_FILE_PATH}")

if __name__ == "__main__":
    monitor_danmu_log()