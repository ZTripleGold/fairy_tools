import base64
import os
import json
import requests
import time

# ========== 已完全匹配你的控制台配置，无需修改 ==========
host = "https://openspeech.bytedance.com"
APPID = "9997763561"
ACCESS_TOKEN = "YU4fvB8B1vWLS5J-SkZPdQ-QlQplsoVi"
SPEAKER_ID = "S_IIFJZwoU1"  # 你的Fairy音色专属ID
RESOURCE_ID = "seed-icl-2.0"  # 豆包声音复刻2.0固定值

# 你的Fairy音频文件路径，确认文件存在即可
AUDIO_FILE_PATHS = [
    r"E:\liveTools\DouBao\Fairy01.wav",
    r"E:\liveTools\DouBao\Fairy02.wav",
    r"E:\liveTools\DouBao\Fairy03.wav",
    r"E:\liveTools\DouBao\Fairy04.wav",
    r"E:\liveTools\DouBao\Fairy05.wav",
    r"E:\liveTools\DouBao\Fairy06.wav",
    r"E:\liveTools\DouBao\Fairy07.wav",
    r"E:\liveTools\DouBao\Fairy08.wav",
    r"E:\liveTools\DouBao\Fairy09.wav"
]


def encode_single_audio(file_path):
    """编码单个音频文件"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"音频文件不存在: {file_path}")
    with open(file_path, 'rb') as f:
        encoded_data = base64.b64encode(f.read()).decode("utf-8")
        audio_format = os.path.splitext(file_path)[1].lstrip('.').lower()
    return encoded_data, audio_format


def upload_one_audio(file_path, idx):
    """上传单个音频到你的Fairy音色"""
    url = f"{host}/api/v1/mega_tts/audio/upload"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer;{ACCESS_TOKEN}",
        "Resource-Id": RESOURCE_ID
    }

    encoded_data, audio_format = encode_single_audio(file_path)
    request_body = {
        "appid": APPID,
        "speaker_id": SPEAKER_ID,
        "audios": [{"audio_bytes": encoded_data, "audio_format": audio_format}],
        "source": 2,
        "language": 0,
        "model_type": 4,
        "extra_params": json.dumps({
            "demo_text": "大家好，我是Fairy，这是我的音色复刻测试",
            "enable_crop_by_asr": True
        }, ensure_ascii=False)
    }

    try:
        response = requests.post(url, json=request_body, headers=headers, timeout=60)
        print(f"\n--- 正在上传第 {idx}/9 个音频: {file_path} ---")
        print(f"响应状态码: {response.status_code}")
        
        result = response.json()
        print("接口响应:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 官方文档：StatusCode=0为上传成功
        if result.get("BaseResp", {}).get("StatusCode") == 0:
            print(f"✅ 第 {idx} 个音频上传成功，剩余上传次数: {10-idx}")
            return True
        else:
            error_msg = result.get("BaseResp", {}).get("StatusMessage", "未知错误")
            raise Exception(f"上传失败: {error_msg}")
            
    except Exception as e:
        raise Exception(f"第 {idx} 个音频处理失败: {str(e)}")


def check_train_status():
    """查询Fairy音色的训练状态"""
    url = f"{host}/api/v1/mega_tts/status"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer;{ACCESS_TOKEN}",
        "Resource-Id": RESOURCE_ID
    }
    request_body = {"appid": APPID, "speaker_id": SPEAKER_ID}

    try:
        response = requests.post(url, json=request_body, headers=headers, timeout=10)
        print("\n--- 训练状态查询结果 ---")
        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        status = result.get("status")
        if status in [2, 4]:
            print("✅ Fairy音色训练完成！可以开始合成语音")
        elif status == 1:
            print("⏳ 音色正在训练中，请5分钟后再次运行查询")
        elif status == 3:
            print("❌ 音色训练失败，请检查音频样本")
        return result
        
    except Exception as e:
        raise Exception(f"状态查询失败: {str(e)}")


if __name__ == "__main__":
    try:
        # 循环上传9个音频（你的音色剩余10次额度，刚好够用）
        for idx, file_path in enumerate(AUDIO_FILE_PATHS, 1):
            upload_one_audio(file_path, idx)
            time.sleep(3)  # 避免请求过快触发限流
        
        # 上传完成后查询训练状态
        print("\n--- 所有音频上传完成，正在查询训练状态 ---")
        check_train_status()
        
    except Exception as e:
        print(f"\n❌ 程序执行失败: {str(e)}")