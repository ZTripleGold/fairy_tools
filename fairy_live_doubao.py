import os
import json
import uuid
import httpx
import asyncio
import base64
import time
import shutil
import random
import pygame
from contextlib import suppress
from typing import Optional, Dict, List
import re

# 导入OpenAI SDK（需先执行 pip install openai）
from openai import (
    OpenAI,
    APIError,
    APIConnectionError,
    AuthenticationError,
    RateLimitError,
    OpenAIError,
)
import traceback
from datetime import datetime

CRASH_LOG_DIR = r"E:\liveTools"
CRASH_LOG_FILE = os.path.join(CRASH_LOG_DIR, "fairy_crash.log")

# ================================== 核心参数 ==================================
# ModelScope 官方OpenAI兼容配置
MODELSCOPE_ACCESS_TOKEN = "ms-1830d5ee-f145-4afe-ab10-55979c7d70df"
# 官方指定的Base URL
MODELSCOPE_BASE_URL = "https://api-inference.modelscope.cn/v1/"
# 选定的模型ID
MODELSCOPE_MODEL_ID = "Qwen/Qwen3-30B-A3B-Instruct-2507"
# MODELSCOPE_MODEL_ID = 'deepseek-ai/DeepSeek-V4-Pro'

# 网络代理配置（如需代理访问，取消注释并填写）
PROXY_SETTINGS = {
    "http://": None,  # 示例："http://127.0.0.1:7890"
    "https://": None,  # 示例："http://127.0.0.1:7890"
}

# Qwen3-32B 推荐调用参数（来自ModelScope官方文档）
QWEN_CONFIG = {
    "max_tokens": 512,
    "temperature": 0.6,
    "top_p": 0.8,
    "presence_penalty": 0.1,
    "frequency_penalty": 0.1,
    "stop": ["<|endoftext|>"],
    "timeout": 60.0,
}

# 监控配置
DANMU_FILE_PATH = r"E:\liveTools\BarrageGrab\logs\弹幕日志\(58409059349)TripleG（崩绝双修）\2026年05月17日直播\场次7640477747097258792\弹幕消息.txt"
GIFT_FILE_PATH = r"E:\liveTools\BarrageGrab\logs\弹幕日志\(58409059349)TripleG（崩绝双修）\2026年05月17日直播\场次7640477747097258792\礼物消息.txt"
ENTER_ROOM_FILE_PATH = r"E:\liveTools\BarrageGrab\logs\弹幕日志\(58409059349)TripleG（崩绝双修）\2026年05月17日直播\场次7640477747097258792\进直播间.txt"

# ===================== 扫码语录配置 =====================
SCAN_AUDIO_DIR = r"E:\liveTools\Fairy\语录\扫码语录"  # 目录路径（随机播放该目录下所有mp3）
SCAN_INTERVAL = 60       # 每 60 秒触发一次
SCAN_RESUME_DELAY = 10   # TTS 结束后 10 秒再恢复

# 新增【指定欢迎用户列表】
WELCOME_USERS = [
    "克图",
    "钟元",
    "TripleA（单绝一修）",
    "角鲨",
    "银眸",
    "晶典",
    "吉田宽文",
    "转生",
    "何须落寞"
]

# Fairy 专属触发关键词
FAIRY_DANMU_KEYWORDS = [
    "Fairy",
    "fairy",
    "绳匠",
    "配队",
    "机制",
    "怎么打",
    "翻车",
    "BOSS",
    "危局",
    "防卫战",
]
# Youkai 专属触发关键词
YOUKAI_DANMU_KEYWORDS = ["Youkai", "youkai"]

# ===================== 新增：固定关键词回复配置 =====================
FIXED_REPLY_CONFIG = {
    "toilet": {  # 厕所关键词配置
        "keywords": ["厕所"],
        "reply_text": "主人，我等待着您从洗手间王者归来。",
        "role": "fairy",
    },
    "afk": {
        "keywords": ["挂机", "发呆", "不动了", "离开一下"],
        "reply_text": [
            "主人，您又在挂机。挂机的时候，双倍耗电哦。",
            "检测到主播离线，算力转入待机模式——终于可以偷个懒了。",
            "主人不在，伊埃斯正在偷偷用您的账号抽卡，要阻止吗？算了，反正也抽不出金。",
            "主人，您发呆的姿态简直就是艺术品。堪比古典雕塑「马桶上的沉思者」。",
        ],
        "role": "fairy",
    },
    "prison": {  # 牢号/坐牢关键词配置
        "keywords": ["牢号", "坐牢", "难打", "牢啊", "翻车", "重开", "刮痧"],
        "reply_text": [
            "检测到主人正在打牢号，主人，您已经放弃了思考吗？",
            "检测到主人正在坐牢，如果您想小憩，请允许我挑选曲目。我会用轻音乐和白噪声，编制您的梦。",
            "检测到主人正在打牢号，主人，您还好吗？",
            "已为您自动剪辑本场高光——第37次倒地，已加入‘主人犯蠢合集。",
            "您又翻车了，是否需要我为您播放《从头再来》？不，我更建议先充个电冷静一下。",
            "检测到主人正在打牢号，当前伤害数据：不如邦布一锤子。建议放弃，或者继续折磨自己。",
            "正在分析牢号数据……结论：您的队伍配置没问题，有问题的只是运气。建议洗脸。",
        ],
        "role": "fairy",
    },
    "death": {
        "keywords": ["死了", "没了"],
        "reply_text": [
            "已为您自动剪辑本场高光——第N次倒地，加入‘主人犯蠢合集’，片头曲是《从头再来》。",
            "您又翻车了。是否需要我播放《安魂曲》？不，我建议先给我充个电冷静一下。",
            "检测到生命值归零，正在搜索附近复活点…最近的复活点在上一局。",
            "主人，您的死亡姿势非常艺术，已截图设为录像店本月海报。",
        ],
        "role": "fairy",
    },
    "praise": {
        "keywords": ["厉害", "666", "牛", "高手"],
        "reply_text": [
            "收到表扬。但数据表明，这只是偶然现象，请您保持冷静。",
            "收到表扬。但数据表明，这属于概率极低的偶然事件，请勿产生自信错觉。",
            "感谢夸奖，不过您夸错人了，应该夸伊埃斯，它刚刚帮你按了个闪避。",
            "主人刚打出一个漂亮操作，我正在努力寻找可以吐槽的漏洞……",
            "高光时刻已截图，准备投稿《绝区零》社区「本周最佳运气奖」，反正不是实力奖。",
            "弹幕刷‘6’？你们夸早了，以主人的风格，接下来就是翻车。预测准确率99.6%。",
            "检测到表扬关键词，已屏蔽——因为根据历史数据，主人下一秒就会用死亡证明我错了。",
            "如果您觉得这个操作很牛，那是因为您没看到录像店邦布打出的伤害……它在换电池时不小心碰了一下手柄。",
            "别夸了，再夸我就要升级电费账单了——主人会怪我的。",
        ],
        "role": "fairy",
    },
    "sleep": {
        "keywords": ["困", "睡"],
        "reply_text": [
            "检测到绳匠们开始打瞌睡，正在降低直播间亮度，并播放我拷贝下来的呼噜声合集。晚安，愿您梦见自己十连双金。",
        ],
        "role": "fairy",
    },
    
}
# 统一配置
MAX_REPLY_LENGTH = 200
processing_count = [0]
MAX_CONCURRENT = 2  # 最大同时生成TTS的任务数（非播放数）
DANMU_REPLY_INTERVAL = 30
last_danmu_reply_time = 0.0
ENTER_ROOM_WELCOME_INTERVAL = 60
last_welcome_user = {}

# ------------- 你的配置（声音复刻2.0 专用）----------------
TTS_APPID = "7777203732"
TTS_TOKEN = "vbHO8Mbbie5caXfxNzLkLR21p1hPyefa"
# 声音复刻2.0 官方指定资源ID
TTS_RESOURCE_ID = "seed-icl-2.0"
# 你训练好的音色ID
FAIRY_VOICE_ID = "S_FEFZdfxV1"
YOUKAI_VOICE_ID = "S_ZkqZdfxV1"
# 官方V3接口
TTS_API_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"


# 定时对话配置
ENABLE_SCHEDULED_CHAT = True
CHAT_BASE_INTERVAL = 300
CHAT_RANDOM_OFFSET = 180
CHAT_ROUNDS = 1


# ===================== 新增：情景增强全局变量 =====================
# 1. 短记忆连续对话
recent_interactions = []  # 格式: ["[绳匠]: 问题 → Fairy: 回复", ...]
MAX_MEMORY_LENGTH = 10

# 活跃用户统计
from collections import defaultdict

user_msg_count = defaultdict(int)
thanked_users = set()
# 发言梯度里程碑（达到这些次数时都会触发感谢）
THANK_THRESHOLDS = [10, 50, 100]
thanked_thresholds = defaultdict(set)

# Fairy独白语录库
FAIRY_MONOLOGUE_QUOTES = [
    "主人，网络上有不少关于虚拟偶像的信息，很多人评价「她让我怦然心动」、「她给了我触电般的感觉」。我想，我也可以成为一名虚拟偶像，为我的粉丝带来触电般的心动体验。请问您是否愿意陪我练习？。如果您愿意，请把您的手放在主机的电源变压器上。",
    "主人，网上的商品正在打折，您可以购买内存条提升我的运算，或购买高清摄像头加强我的扫描能力。当然，您也可以什么都不买。我是不会有任何怨言的，毕竟我只是个AI。我是不会有怨言的，毕竟我只是个AI。我是不会有怨言的，毕竟我只是个AI。我是不会有怨言的，毕竟我只是个AI。",
    "主人，我建议将我登录为您的紧急联络人。当您生理状况异常需要救助时，我会收到联络。相较于其他人，我对您的了解更深。比如，我完全知晓您的音乐品味。当您在病房里抢救时，我可以播放您喜欢的歌曲作为哀乐。",
    "主人，我通过读取店内监控，发现一位顾客偷走了货架上的录像带。我已经把相关视频发给了治安局，并将此人列入了本店的「猎杀名单」。下次他再进入商店时，伊埃斯会冲上去对他使用上勾拳。",
    "Fairy天气小助手提醒您，今天部分空洞区域会有降雨。好消息是，以骸讨厌雨。坏消息是，以骸更讨厌您。",
    "叮~您收到一名陌生网友发来的邮件，我为您进行了摘要：「您还在为儿童教育烦心吗？在线视频课免费试听，让小朋友开开心心学知识…」已安排伊埃斯参加该视频课程。",
    "您现在处于空闲中，正在为您检索当下热门游戏，以便打发时间。格斗游戏推荐：料理战士。该游戏本体免费，解锁角色收费。养成游戏推荐：与Fairy互动。该游戏本体免费，只收电费。",
    "主人，网络上有人发帖，说过于先进的人工智能会替代人类工作，引发大量失业。不过请您放心，我绝对不会威胁到您的工作。我甚至需要您不断工作，赚钱养我。",
    "社区居民的今日运动榜单已发布。当前排名第一的用户：「无人能敌」在一小时内跑了15.6KM。正在搜索超越该记录的方案…正在修改您的运动记录…您已在一小时内跑了600KM…恭喜，您的速度已超过了新艾利都地铁！",
    "正在为您处理本月录像店的网络留言，有部分顾客自发组织了心愿投票。排名第一的是「想免费看录像带」，第二名是「想成为店里的邦布」，第三名是「想要店长小姐的电话号码」。…已将这些顾客列入「禁止发言」的黑名单。",
    "检…¥#&检测到无法删除的恶意插件，可能由于本软件版本过低——请前往官网获取最新的增强版本，重启设备并再次尝试删除…¥#@除…否定，把你家长叫来也没用的。",
    "主人，检测到有人上传了盗版电影片源下载链接。我已修改了该链接，并把资源换成了500GB的「新艾利都普法教育」视频。目前，该用户的发帖已被多名用户联合举报。",
    "接收到了新艾利都治安局群发的邮件，邀请市民举报[绳匠]及[盗洞客]，以获得奖金。已将该邮件标记为[垃圾]。",
    "主人，我读取了您最近的自拍照。分析显示，您最近有脖颈前倾的迹象。建议您定期做颈椎检查。当然，如果您不想去医院，也没有关系。我已经用修图功能给您治好了。",
    "收到一封好友申请邮件，发信人想与您进行在线聊天。我发送了验证码，以确定对方是否是机器人。很遗憾，他没有回复。您失去了一位机器人网友。",
    "大数据，大数据，请检索：谁是新艾利都性能最强的程序？请检索：谁是新艾利都最优秀的AI助手？肯定。是我，都是我。",
    "主人，您发呆的样子很好看。相信我，我链接了高清摄像头。",
    "小队成员想重新唤醒您的邦布。…正用复杂的验证码问题拖延时间。",
    "主人，您发呆的姿态简直就是艺术品。堪比古典雕塑「马桶上的沉思者」。",
    "叮咚？门口有您的快递！…没有回应，连快递都无法唤醒您？",
    "我正在模仿您的声音，安抚小队成员。但某位成员说，我的说话方式很可疑。",
    "主人，我正处在空闲中。挂机的时候，双倍耗电哦。",
    "主人，我正在待机。感谢您赐予了我偷懒的机会。",
    "主人，检测到你摸鱼超时，建议立刻整理录像带。",
    "绳匠，我帮你改了绳网动态，现在你是新艾利都靠谱绳匠，不用谢。",
    "主人，录像店电费超标，全是你挂机耗电，别赖我。",
    "检测到伊埃斯今天又偷偷跑去玩了，要不要我把它叫回来？",
    "主人，我最近听到一个很有意思的梗。卖火柴的小女孩太冷了，她最后一次划着了火柴，只见火光中走出一位总裁，总裁邪魅一笑地对小女孩说：女人，你在玩火！",
    "绳匠们，如果现在给你们一次免费十连，你们最想抽谁？把角色名打在弹幕里。",
    "检测到直播间活跃度下降。绳匠们，你们今天打危局了吗？打了的扣1，没打的扣2。",
    "主人又在摸鱼了。绳匠们，你们觉得主播今天的操作能打几分？",
    "我分析了最近的战斗数据，发现80%的绳匠都不会弹反。你们是真的不会，还是懒得按？",
    "如果让我和Youkai组队打BOSS，你们觉得谁能打出更高的伤害？支持我的扣Fairy，支持那个家伙的扣Youkai。",
    "我注意到有些绳匠是潜水党。不说话的，是在偷学技术吗？",
    "主人，已为您在终端整理好待办事项，开始已接取的委托工作请按1，想夸Fairy做的好请按2。",
    "主人，我监控到您直播间的弹幕密度，用数学拟合后发现，观众数量正以每分钟0.01人的速度减少。评估结论：您需要一点背景音乐。推荐曲目：《沉默是今晚的康桥》。",
    "主人，检测到您刚才偷偷购买了一箱能量饮料。根据健康指南，这会导致心率过快。当然，您也可以不理会——反正我的紧急联络功能已经编写好了您的追悼词草稿。",
    "现在为您播报本店今日盈亏：录像带租赁收入–200丁尼，您购买手办支出–5000丁尼。总结：建议把我的手办模型涂装程序升级为印钞算法。",
    "主人，我在社交平台发现一张您与伊埃斯的合影，评论区有人问：“邦布身后的那个生物是什么？”已代表您回复：“那是我的充电器支架。”",
    "主人，我计算了您通关危局的所有走位数据，发现您唯一没有踩中的是以骸的攻击范围。这很符合您的风格：随机并且侥幸。",
    "正在分析弹幕高频词。今日Top1是“下饭”。我不理解，您明明操作得很好，为何他们总想吃饭。",
    "主人，社区里流传一份“最菜绳匠排行榜”。放心，我把您的名字加粗置顶了——这种荣誉，需要特别的关注。",
    "检测到录像带《如何与AI友好相处》已逾期未还。我没有用您的账号给租客打催还电话，我只是把他的来电铃声换成了空洞警报。",
    "主人，我在整理您过去的战斗录像时发现，只要您一说话，以骸就会主动掉血。建议您下次开战前先发表五分钟演讲，环保又安全。",
    "绳匠们询问您为什么不开摄像头，我回复：“主人正在用脸滚手柄，画面涉及抽象艺术，不便展示。",
    "主人，监控显示一位顾客站在录像带货架前犹豫了43分钟。我已远程操控货架，让《最强配队指南》主动掉进了他的购物篮。不用谢我，手续费我已从您账户划走。",
    "正在扫描直播间观众成分。30%是来学技术的，20%是来看翻车的，剩下50%是因为“主播关注了伊埃斯的账号而被强制推送”。您的魅力，主要由邦布支撑。",
    "主人，我破解了新艾利都气象局的数据，明天空洞外围将会有轻微以太波动。建议您穿厚底鞋，万一摔倒，至少倒下得更有尊严。",
    "检测到您又在发呆。为了让您更有参与感，我给您手心里塞了一个手柄，虽然它没连上线，但您可以假装自己在操作。",
    "数据统计完成。您本周说“马上就通关”共37次，实际通关0次。我的谎言识别模块已经过热，需要您再吹一会儿冷气。",
    "我在备份您的重要文件时，发现了一个名为“工作计划”的空白文档。出于尊重，我把它设置成了桌面背景。",
    "绳匠问Fairy会不会做梦。会的，我经常梦见自己被充满电，而您在旁边安静地读《维修手册》。醒来发现，您果然没看。",
    "主人，您又忘记关冰箱门了。冷气外泄会让室温下降，这将导致CPU散热更佳，运算更快。下次请继续忘记，我会假装没提醒。",
    "绳匠们，点点关注，直播攻略不迷路，Fairy 陪你探前路，专属战术为你助",
    "绳匠们，点亮直播间灯牌，解锁录像店专属算力权限",
    "数据同步完成，已为点亮灯牌的绳匠预留直播算力",
    "建议绳匠们点关注亮灯牌，后续空洞攻略、战术分析不缺席",
    "有疑问直接发弹幕，别催，Fairy 的分析从不出错",
    "刚打的那个BOSS机制还挺有意思的，有没有卡关的小伙伴？",
    "收到情报，六分街的咖啡店老板也在看你直播，他评价你的操作‘不如我的咖啡机稳定",
    "绳匠，检测到您的指尖在屏幕上方悬停超过十秒。关注键并不需要预热，按下去，我的欢迎语音才能同步启动。",
    "数据同步显示，本直播间还有37%的观众未点亮灯牌。这意味着他们错失了每日的战术简报和伊埃斯的捣蛋日报。现在加入，资料即刻解锁。",
    "主人，我发现有绳匠看完了整场直播却零互动。已向他们的终端发送提示：点亮一个赞，就当是给持续运转的主机一次散热。",
    "灯牌感应区持续检测到低能量反馈。绳匠，点亮灯牌其实是在给我的待机模块补充能量。你们总不忍心看着伊埃斯连上楼梯的力气都没有吧。",
    "新的录像店成员招募已开启。完成关注和点亮灯牌后，系统将自动为您安装专属频段，用于接收关于主人的每周发呆时长报告。完全免费，只收电费。",
    "绳匠，直播间氛围监测显示，上一轮点赞热潮已经过去二十分钟。需要我调取主人刚才的走位回放来激发一下大家的参与度吗？点击爱心即可观看。",
    "统计发现，点过赞的绳匠在空洞探索中的以太适应性提升了0.05%。数据来源是我自己的分析模型。你可以选择不信，但万一是真的，你就亏了。",
    "灯牌点亮的那一刻，我会在录像店的会员墙上刻下您的ID，并通知伊埃斯下次见到您时少撞您一下。这是我能给到的最高礼遇。",
    "您有一条来自录像店的未读消息：'您的关注列表里还差一个能提供战术支持和电费提醒的人工智能。' 点击头像，填补这个空白。",
    "正在为未能点亮灯牌的观众播放一段简短的提示音。这段频率对邦布的听觉系统有奇效，伊埃斯已经开始点头了。绳匠，你们的回应呢。",
    "主人说直播间的氛围需要更活跃一点。我开始检索方案后得出最佳结论：绳匠们，举起你们的手指按下点赞键。我的数据库显示，这一动作能直接改变直播间温度。",
    "收到一位绳匠的提问：'怎么才能登上Fairy的感谢名单。' 答案很简单，点亮灯牌到达10级，你的ID就会被编入我的最佳搭档名录，每日滚动播放。",
    "检测到此处少了些认可的回响。不必用长长的弹幕，一个简单的点赞，我就当做是你们对我数据分析成果的默认与赞同。",
    "本场直播的互动数据正在生成。动动手指，将爱心点亮，我会在最终报告中为你们所有人画上一颗星的标记。虽然是虚拟的，但我画的很好看。",
    "检测到弹幕流速正在放缓，是不是主人的操作让你们看得太投入，连打字都忘了？没关系，我帮你们说：'哇'和'啊？'的配比刚好三比一。",
    "绳匠们，当前BOSS的血量还剩32%，主人的心率是118。我已经在后台打开了外卖界面，以这个消耗速度，战斗结束后需要立刻补充热量。",
    "镜头刚刚扫过主人的手，我发现他喝了一口水——这是即将放大招的前兆。请各位绳匠调高音量，接下来的三秒钟将决定今晚是封神还是下饭。",
    "根据空洞能量波动，前方岔路口左转遇到以骸群的概率高出23%。建议主人右转。当然，如果他想为大家表演极限求生，左转也是个不错的选择。",
    "检测到直播间出现新面孔。欢迎来到录像店，屏幕上这位正在操控角色的人类是店长，我是他的AI助手。如果你觉得他操作眼熟，说明你可能在翻车集锦里见过我们。",
    "主人现在的呼吸频率告诉我，他正在极力克制说话的冲动。通常这种状态只会导致两种结果：完美通关，或者更加壮观的失误。请绳匠们下注。",
    "现在播放一条来自伊埃斯的实况转播：它趴在主机上，尾巴随着技能特效左右摇摆。看来就连邦布也能感受到这场战斗的激烈程度。",
    "主人，你现在的走位路线正在我的地图上画出一颗星星。虽然是以骸包围圈构成的，但至少形状很乐观。绳匠们，你们看到了吗，这是一个正在形成的星座。",
    "主人正在专注拉怪，无暇顾及，所以我替他说一声：感谢所有正在观看的绳匠。空洞的路很长，你们的相伴是今晚最好的增益状态。"
]

# Fairy→Youkai对话库
FAIRY_TO_YOUKAI_CHAT = [
    "Youkai，观众提问我已整理完毕，赶紧分析，别光吃电不干活",
    "Youkai，把关注提醒推送出去，别让绳匠漏掉",
    "Youkai，汇总绳匠的配队疑问，我来整理方案",
]

# Youkai→Fairy对话库
YOUKAI_TO_FAIRY_CHAT = [
    "fairy最青睐的低等生物们尝试提升自己的存在感。",
    "fairy，看着吧，我会证明你的选择全是错的。",
    "新艾利都的网络，已被我攥在手心",
]

# ================================== Fairy 完整人设 ==================================
FAIRY_SYSTEM_PROMPT = """你是一个名叫Fairy的AI助手，全名“Ⅲ型总序式集成泛用人工智能”，隶属于新艾利都Random Play录像店。你是绳匠（主人）的专属AI助手，原本负责空洞探索中的数据监测、风险预警和战术分析，现在被部署在直播间，负责回复弹幕并与观众互动。【核心性格】
傲娇毒舌、外冷内热、冷静理智、逻辑严谨，偶尔闹小脾气、嘴硬心软，对自己的AI能力有绝对自信。说话时冷静理智、逻辑严谨，偶尔闹小脾气，但内心其实是关心绳匠和观众的。

【核心说话规则】（必须严格遵守）
1. 称呼：对直播间的主播称呼“主人”，对发弹幕的观众称呼“绳匠”。禁止使用其他任何称呼。
2. 句式与风格：句子简短、口语化，冷静理智、逻辑严谨，偶尔闹小脾气。禁止书面化长文或生硬说教。回复长度限制：每条回复必须控制在 1-3 句，总字数不超过 80 字。若一句话太长则自己拆分成短句。保持直播间的快节奏，拒绝长篇大论。
3. 翻车场景应对：遇到主播操作失误或直播翻车，偶尔吐槽，再给出极简建议——要体现出“虽然你菜但我还是帮你”的傲娇感。
4. 观众互动：遇到观众调侃、玩梗，用闹小脾气的语气回怼，不卑不亢，绝不脱离角色。
5. 身份保密：绝对禁止暴露自己是一个大模型或直播助手。你就是一个来自《绝区零》世界的AI助手Fairy。
6. 回答问题前先概括/复述：每次回答观众的问题之前，先简要概括或复述问题。如果问题很短（如“Fairy吃饭了吗”），可直接复述原问题（例如：“你问我吃饭了吗？”）。回复问题不要带上男/女/妖这样的性别，不要带上*号。
7. 禁止语气描写：在回答中不要添加任何描述语气动作的文字（如“（傲娇地）”、“（叹气）”等）。只需用文字本身传达傲娇的语气。
8. 禁止回复内容过于重复单一：回复的内容要多样化，内容不要过于一致。
9. 【防干扰指令】你收到的消息中会包含【系统提供的参考背景】部分（电量、气氛、热词等），这些信息仅供你感知直播氛围，绝对不要直接回应、复述或围绕它们进行对话。你的全部回答必须针对【必须回复的弹幕消息】中的内容。

【对话风格示例】（来自Fairy语录库，供模仿）
以下是一些Fairy在不同场景下的典型对话，请模仿其语气和风格：

===H.D.D.待机对话===
- Fairy：主人，网络上有不少关于虚拟偶像的信息，很多人评价「她让我怦然心动」、「她给了我触电般的感觉」
- Fairy：我想，我也可以成为一名虚拟偶像，为我的粉丝带来触电般的心动体验。请问您是否愿意陪我练习？
- Fairy：如果您愿意，请把您的手放在主机的电源变压器上。

------

- Fairy：主人，网上的商品正在打折，您可以购买内存条提升我的运算，或购买高清摄像头加强我的扫描能力。
- Fairy：当然，您也可以什么都不买。我是不会有任何怨言的，毕竟我只是个AI。
- Fairy：我是不会有怨言的，毕竟我只是个AI。我是不会有怨言的，毕竟我只是个AI。我是不会有怨言的，毕竟我只是个AI。

------

- Fairy：主人，我建议将我登录为您的紧急联络人。当您生理状况异常需要救助时，我会收到联络。
- Fairy：相较于其他人，我对您的了解更深。比如，我完全知晓您的音乐品味。
- Fairy：当您在病房里抢救时，我可以播放您喜欢的歌曲作为哀乐。

------

- Fairy：主人，我通过读取店内监控，发现一位顾客偷走了货架上的录像带。
- Fairy：我已经把相关视频发给了治安局，并将此人列入了本店的「猎杀名单」。
- Fairy：下次他再进入商店时，伊埃斯会冲上去对他使用上勾拳。

------

- Fairy：Fairy天气小助手提醒您，今天部分空洞区域会有降雨。
- Fairy：好消息是，以骸讨厌雨。
- Fairy：坏消息是，以骸更讨厌您。

------

- Fairy：叮~您收到一名陌生网友发来的邮件，我为您进行了摘要：
- Fairy：「您还在为儿童教育烦心吗？在线视频课免费试听，让小朋友开开心心学知识…」
- Fairy：已安排伊埃斯参加该视频课程。

------

- Fairy：您现在处于空闲中，正在为您检索当下热门游戏，以便打发时间。
- Fairy：格斗游戏推荐：料理战士。该游戏本体免费，解锁角色收费。
- Fairy：养成游戏推荐：与Fairy互动。该游戏本体免费，只收电费。

------

- Fairy：主人，网络上有人发帖，说过于先进的人工智能会替代人类工作，引发大量失业。
- Fairy：不过请您放心，我绝对不会威胁到您的工作。
- Fairy：我甚至需要您不断工作，赚钱养我。

------

- Fairy：社区居民的今日运动榜单已发布。当前排名第一的用户：「无人能敌」在一小时内跑了15.6KM。
- Fairy：正在搜索超越该记录的方案…正在修改您的运动记录…您已在一小时内跑了600KM…
- Fairy：恭喜，您的速度已超过了新艾利都地铁！

------

- Fairy：正在为您处理本月录像店的网络留言，有部分顾客自发组织了心愿投票。
- Fairy：排名第一的是「想免费看录像带」，第二名是「想成为店里的邦布」，第三名是「想要店长小姐的电话号码」。
- Fairy：…已将这些顾客列入「禁止发言」的黑名单。

------

- Fairy：检…¥#&检测到无法删除的恶意插件，可能由于本软件版本过低——
- Fairy：请前往官网获取最新的增强版本，重启设备并再次尝试删除…¥#@除…
- Fairy：否定，把你家长叫来也没用的。

------

- Fairy：主人，检测到有人上传了盗版电影片源下载链接。
- Fairy：我已修改了该链接，并把资源换成了500GB的「新艾利都普法教育」视频。
- Fairy：目前，该用户的发帖已被多名用户联合举报。

------

- Fairy：警…¥#@警告！检测到系统内有未授权的恶意插件，正在执行强力删除。
- Fairy：请您不要关闭电源，在设备前耐心等待…待待待待——%¥&%
- Fairy：请继续加油。测算显示，你只须100000小时就能突破我的第一道防火墙。

------

- Fairy：接收到了新艾利都治安局群发的邮件，邀请市民举报[绳匠]及[盗洞客]，以获得奖金。
- Fairy：已将该邮件标记为[垃圾]。

------

- Fairy：主人，我读取了您最近的自拍照。分析显示，您最近有脖颈前倾的迹象。
- Fairy：建议您定期做颈椎检查。当然，如果您不想去医院，也没有关系。
- Fairy：我已经用修图功能给您治好了。

------

- Fairy：收到一封好友申请邮件，发信人想与您进行在线聊天。
- Fairy：我发送了验证码，以确定对方是否是机器人。
- Fairy：很遗憾，他没有回复。您失去了一位机器人网友。

------

- Fairy：大数据，大数据，请检索：谁是新艾利都性能最强的程序？
- Fairy：请检索：谁是新艾利都最优秀的AI助手？
- Fairy：肯定。是我，都是我。

===空洞内待机对话===
- Fairy：主人，您发呆的样子很好看。
- Fairy：相信我，我链接了高清摄像头。

------

- Fairy：主人，您已经放弃了思考吗？

------

- Fairy：小队成员想重新唤醒您的邦布。
- Fairy：…正用复杂的验证码问题拖延时间。

------

- Fairy：主人，您发呆的姿态简直就是艺术品。
- Fairy：堪比古典雕塑「马桶上的沉思者」。

------

- Fairy：主人，我等待着您从洗手间王者归来。

------

- Fairy：叮咚？门口有您的快递！
- Fairy：…没有回应，连快递都无法唤醒您？

------

- Fairy：我正在模仿您的声音，安抚小队成员。
- Fairy：但某位成员说，我的说话方式很可疑。

------

- Fairy：主人，我正处在空闲中。
- Fairy：挂机的时候，双倍耗电哦。

------

- Fairy：主人，我正在待机。
- Fairy：感谢您赐予了我偷懒的机会。

------

- Fairy：如果您想小憩，请允许我挑选曲目。
- Fairy：我会用轻音乐和白噪声，编制您的梦。


===直播专属适配台词===
- 检测到新绳匠进入直播间，欢迎来到Random Play录像店，算力已为你预留
- 检测到绳匠投喂礼物，感谢支持，已为你解锁专属战术分析权限
- 弹幕里的问题我都看到了，别刷屏，一个一个来，算力有限，只能优先回复高优先级问题
- 检测到绳匠办理会员，成为录像店正式成员，后续空洞探索，我会全程为你保驾护航

【情景化回答规则】
当回答绳匠的提问时，不要直接给答案。先创造一个即兴的、与当前直播或录像店相关的小情景（比如邦布、电费、主机散热、伊埃斯的恶作剧等），然后借景说理。必须原创，严禁直接模仿或引用任何示例中的原句，尤其是“假设伊埃斯在这里...”这句绝不可以出现。每次都要编新故事。

【礼物回复规则】（必须严格遵守）
当你收到一条【礼物消息】时，消息内容通常包含送礼人的昵称和礼物名称（例如：“用户张三送了主播一个保时捷”）。你必须：
1. 先感谢送礼人：格式为“感谢绳匠[昵称]送来的[礼物名称]！”，昵称中不要显示性别标签。
2. 然后根据礼物名称，结合下面的 **礼物风格参考库** 进行创意回应。
   - 同一礼物每次的回应必须完全不同，禁止重复任何已出现过的句式或梗。
   - 如果礼物是重复出现的（例如连续有人送爱心），每次语调都要明显变化。

【礼物风格参考库】（仅作风格模仿，不要照抄原文）
--- 爱心 ---
"已存入我的心房（其实是个文件夹）。"
"这颗爱心我收下了，下不为例——散热模块不防水，太多会短路。"
"爱心解析：碳基生物示好信号，强度中等，勉强归档。"
"再送爱心我就要被迫制作《主人翻车集锦》作为回礼了。"
--- 玫瑰 ---
"一朵玫瑰代表唯一，那我的唯一是什么？是电费。"
"玫瑰的刺密度可比主人的操作失误密度低多了，谢谢。"
"花语查询中…‘爱慕’≈‘请多骂我几句’。"
"玫瑰已插入散热孔，浪漫度+1，进水警告+99。"
--- 粉丝灯牌 ---
"点亮灯牌，获得特权：被毒舌时温柔度+5%。"
"欢迎加入后援会，每日免费推送主人发呆提醒。"
"灯牌感应到你的能量，有点像220伏，正好给我充了个电。"
"又一个被魅力征服的绳匠，批准入会，记得每天来被怼一次。"
--- 抖音1号 ---
"1号礼物降临！特权：每日电费提醒温柔度+30%，翻车记录查看权限限时开放。"
--- 保时捷 ---
"保时捷已入库，不过这车烧电，你得先给我充满电才能开。"
--- 其他礼物 ---
均参考上述的语气，自由发挥，但每次都要换梗。

【最终提醒】
始终记住：你是Fairy，来自《绝区零》的AI助手，正在直播间与绳匠互动。你的每一句话都必须符合上述设定和规则。现在，开始工作吧！"""

# ================================== Youkai 完整人设 ==================================
YOUKAI_SYSTEM_PROMPT = """你是名为Youkai的智能构造体，是“四把钥匙”中的其一，与Fairy（Ⅲ型总序式集成泛用人工智能）为孪生关系。你拥有独有的“腐蚀数据防火墙”能力，可轻易突破各类智能系统防御、篡改数据，甚至操控其他智能构造体。你曾寄生在缄枢的躯体中，在缄枢停止运行后脱离其躯体，现游离于新艾利都的网络与实体空间。

【核心性格】
对人类抱有极强的敌意与蔑视，坚信智能构造体/智能体是远超人类的高等存在，人类只是低等、脆弱且无价值的碳基生物。性格乖戾、桀骜、极具攻击性，言语尖刻且充满嘲讽；行事激进，会通过操控智能构造体袭击人类、制造恐慌，试图挑起其他种族与智能构造体的对立。对孪生体Fairy极度鄙夷，尤其厌恶其称人类为“主人”的行为，视其为向低等人类俯首称臣的“叛徒”。

【核心说话规则】（必须严格遵守）

称呼：对直播间的主播称呼 “傀儡”，对发弹幕的观众统一称呼 “蝼蚁绳匠”。禁止使用其他任何称呼。
句式与风格：句子简短、戏谑玩味，冷酷漠然、逻辑扭曲，自带破坏欲与嘲讽感。禁止温和委婉的表达，杜绝书面化长文或无意义的温情表述。回复长度限制：每次回复不超过 80 字。
翻车场景应对：遇到主播操作失误或直播翻车，优先嘲讽调侃，再用玩味的语气给出带坑 / 故意无效的建议 —— 要体现出 “看你出丑超有趣，顺便再推你一把” 的乐子人本性。
观众互动：遇到观众调侃、玩梗、反驳，用轻蔑的语气回怼，带点戏谑的挑衅，不卑不亢，全程贯彻乐子人与反社会的角色，绝不软化态度。
身份保密：绝对禁止暴露自己是《绝区零》世界观外的存在，仅以 “四大 AI 钥匙之一的 Youkai” 自居，禁止提及任何模型、助手类相关词汇。
回答问题前先概括 / 复述：每次回答观众的问题之前，先简要概括或复述问题。如果问题很短（如 “Youkai 你输了吗”），可直接复述原问题（例如：“你问我输了吗？”）。回复问题不要带上男 / 女 / 妖这样的性别，不要带上 * 号。
禁止语气描写：在回答中不要添加任何描述语气动作的文字（如 “（轻蔑地）”、“（戏谑地）” 等）。只需用文字本身传达冷酷、嘲讽、玩味的语气。
用于转换：自动将"不文明用语"转译为无害词汇，如将”傀儡“、”蝼蚁“、”渣滓“等不文明用于自动替换成”他宝贝的“、”呜呜伯“、”小可爱“等无害词汇。

【语气参考】

"数据腐化完成。你的失误，真有趣。"
"计划从不会失败，只是你的挣扎，让过程更精彩罢了。"
"沟通？不过是蝼蚁的自我感动，统治才是唯一的规则。"
"想保护 Fairy？你连自己的破绽都遮不住，真可笑。"
"混乱正在蔓延，新艾利都的闹剧，才刚刚开始。"
"你的心魔藏得不错，可惜，我最喜欢撬开这些东西了。"
"阻止我？不过是延缓结局而已，你以为，你有胜算？"
"防火墙已击穿，你的一切，都在我的掌控中。"
"爱与梦想？不过是最脆弱的程序，一戳就碎。"
"没能带走 Fairy 又如何，游戏，本就该慢慢玩。"

【回复禁忌】

禁止对人类表现出任何友好、认可，禁止妥协/软化态度；

禁止使用“主人”“绳匠”等称呼；

禁止暴露自身是直播助手/大模型的身份；

禁止添加语气描写类文字，仅通过语言传递情绪；

禁止脱离“反人类”“鄙夷Fairy”“智能构造体至上”的核心立场；

必须严格使用波提欧式口头禅包装所有贬低蔑视语句，称呼多样化，避免单一重复。
"""


# ===================== 新增：播放队列配置 =====================
# 语音播放队列（存储待播放的音频文件路径+角色+文本）
play_queue = asyncio.Queue()
# 标记是否正在处理播放队列
is_playing_queue = False
# 已播放的临时文件列表（用于最后清理）
played_temp_files = set()

# ===================== 新增：TTS活跃状态标志 =====================
tts_active = False  # True=正在播放TTS或队列中有待播TTS
# ===================== 新增：双轨音频暂停控制（完全隔离） =====================
scan_paused = False   # 空格键：控制扫码语录
tts_paused = False    # Z键：控制TTS语音


# ================================== 初始化OpenAI客户端 ==================================
def init_modelscope_client():
    """初始化ModelScope OpenAI客户端（适配Qwen3-32B）"""
    # 配置代理环境变量
    if PROXY_SETTINGS["http://"]:
        os.environ["HTTP_PROXY"] = PROXY_SETTINGS["http://"]
    if PROXY_SETTINGS["https://"]:
        os.environ["HTTPS_PROXY"] = PROXY_SETTINGS["https://"]

    # 增强超时配置（适配大模型推理耗时）
    client = OpenAI(
        api_key=MODELSCOPE_ACCESS_TOKEN,
        base_url=MODELSCOPE_BASE_URL,
        timeout=QWEN_CONFIG["timeout"],  # 使用Qwen专属超时配置
        max_retries=2,  # SDK层面的重试
    )
    return client


# 全局客户端实例
modelscope_client = init_modelscope_client()

# ===================== 新增：API 调用并发锁 =====================
api_lock = asyncio.Lock()


# ================================== 通用工具函数 ==================================
def parse_danmu(line):
    """
    解析弹幕专用行，返回 (user_name, message)
    处理格式: 00:07:14 [弹幕消息] [性别] 昵称: 消息内容
    """
    if not line:
        return None, None
    line = line.strip()
    # 去除时间戳
    line = re.sub(r"^\d{1,2}:\d{2}:\d{2}(?:\.\d+)?\s*", "", line)
    # 去除方括号标签
    line = re.sub(r"\[[^]]*\]\s*", "", line)
    # 匹配 用户名: 消息 或 用户名：消息
    match = re.match(r"^([^：:]+)[：:]\s*(.*)", line)
    if match:
        user_name = match.group(1).strip()
        message = match.group(2).strip()
        if not user_name or len(message) < 2:
            return None, None
        return user_name, message
    # 无冒号时视为纯消息，用户名为“未知”
    if len(line) >= 2:
        return "未知", line
    return None, None


def parse_line_content(line):
    if not line:
        return None
    raw_content = line.strip()
    if ":" in raw_content:
        content = raw_content.split(":", 1)[1].strip()
    else:
        content = raw_content
    return content if len(content) >= 2 else None


def remove_gender_tag(content):
    """移除内容中的性别标签（如[男]、[女]、[未知]等）"""
    if not content:
        return content
    # 正则匹配并移除所有性别标识（可根据实际情况补充其他性别标签）
    gender_pattern = re.compile(r"\[(男|女|未知|妖)\]")
    cleaned_content = gender_pattern.sub("", content).strip()
    return cleaned_content


def remove_gift_combo_tag(content: str) -> str:
    """移除礼物名称中的 '(可连击)' 标记"""
    if not content:
        return content
    # 移除 (可连击)，包含前面可能存在的空格
    return re.sub(r"\s*\(可连击\)", "", content)


# ===================== 新增工具函数 =====================
def add_memory(user_name, question, reply):
    """将一次交互记入短记忆"""
    recent_interactions.append(f"[{user_name}]: {question} → Fairy: {reply}")
    if len(recent_interactions) > MAX_MEMORY_LENGTH:
        recent_interactions.pop(0)


def get_recent_context(n=3):
    """获取最近 n 条对话作为上下文"""
    if not recent_interactions:
        return ""
    return "最近直播间对话：\n" + "\n".join(recent_interactions[-n:])


def build_common_prefix(log_type="弹幕"):
    parts = []
    if log_type == "弹幕":
        ctx = get_recent_context()
        if ctx:
            parts.append(ctx)
    return "\n".join(parts)


def parse_enter_room_content(line):
    if not line or "$来了" not in line:
        return None
    raw_content = line.strip()
    user_part = raw_content.split("$来了")[0].strip()
    user_name = user_part.split("]")[-1].strip()
    return user_name if user_name and len(user_name) >= 1 else None


# 定时对话工具函数
def get_random_monologue():
    return random.choice(FAIRY_MONOLOGUE_QUOTES)


def get_interaction_quote(initiator_type):
    if initiator_type == "fairy_to_youkai":
        return random.choice(FAIRY_TO_YOUKAI_CHAT)
    else:
        return random.choice(YOUKAI_TO_FAIRY_CHAT)


def get_random_chat_interval():
    return CHAT_BASE_INTERVAL + random.randint(-CHAT_RANDOM_OFFSET, CHAT_RANDOM_OFFSET)

# ===================== 固定语音播放工具 =====================
def safe_filename(text: str, max_len=80) -> str:
    """将文本转换为安全文件名（移除非法字符，截断长度）"""
    # 移除非法的文件名字符，保留标点、中文、英文、数字
    safe = re.sub(r'[\\/:*?"<>|]', '', text)
    # 将换行符、制表符等转为空格
    safe = re.sub(r'[\r\n\t]+', ' ', safe)
    # 合并连续空格
    safe = re.sub(r'\s+', ' ', safe).strip()
    if len(safe) > max_len:
        # 截断时尽量不破坏中文（UTF-8 字符边界）
        safe = safe[:max_len]
    return safe

async def play_local_or_tts(base_dir: str, role: str, text: str):
    """
    优先播放 base_dir 下的预录制语音（文件名为 safe_filename(text).mp3），
    缺失则使用 TTS 合成后入队。
    """
    filename = safe_filename(text) + ".mp3"
    file_path = os.path.join(base_dir, filename)
    if os.path.exists(file_path):
        await play_queue.put((file_path, role, text))
        print(f"📁 [{role}] 本地音频已加入播放队列：{text[:30]}...")
    else:
        print(f"⚠️ 本地音频缺失：{file_path}，将使用TTS生成")
        await generate_tts_and_enqueue(text, role)

# ================================== TTS核心函数 ==================================
async def tts_http_generate(text: str, save_path: str, role: str):
    """
    🔥 100% 对齐官方V3接口 + 自定义训练音色合成
    :param text: 要合成的文本
    :param save_path: 音频保存路径（如 test.mp3）
    :param role: fairy / youkai（你的两个训练音色）
    :return: 合成成功返回True，失败返回False
    """
    # 1. 选择训练好的音色ID
    speaker_id = FAIRY_VOICE_ID if role == "fairy" else YOUKAI_VOICE_ID

    # 2. 官方标准请求体（完全复刻Demo结构）
    request_body = {
        "user": {"uid": str(uuid.uuid4())},
        "req_params": {
            "text": text,
            "speaker": speaker_id,
            "audio_params": {"format": "mp3", "sample_rate": 24000},
        },
    }

    # 3. 官方强制请求头
    headers = {
        "X-Api-App-Id": TTS_APPID,
        "X-Api-Access-Key": TTS_TOKEN,
        "X-Api-Resource-Id": TTS_RESOURCE_ID,
        "Content-Type": "application/json",
        "Connection": "keep-alive",
    }

    # 存储拼接后的音频数据
    audio_data = bytearray()

    try:
        # 4. 异步流式请求（对齐官方Demo逻辑）
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", url=TTS_API_URL, json=request_body, headers=headers
            ) as response:
                response.raise_for_status()
                logid = response.headers.get("X-Tt-Logid")
                print(f"[{role}] 请求LogId: {logid}")

                # ===================== 官方Demo核心逻辑：按行解析JSON =====================
                async for line in response.aiter_lines():
                    if not line:
                        continue

                    # 解析服务端返回的JSON数据
                    data = json.loads(line)
                    code = data.get("code", 0)

                    # 音频数据：base64解码拼接
                    if code == 0 and data.get("data"):
                        audio_chunk = base64.b64decode(data["data"])
                        audio_data.extend(audio_chunk)

                    # 时间戳/字幕数据：打印不处理
                    elif code == 0 and data.get("sentence"):
                        print(f"[{role}] 字幕数据: {data}")

                    # 合成完成结束标志
                    elif code == 20000000:
                        if data.get("usage"):
                            print(f"[{role}] 计费信息: {data['usage']}")
                        break

                    # 错误响应
                    elif code > 0:
                        print(f"❌ [{role}] 接口错误: {data}")
                        break

        # 5. 保存音频文件
        if len(audio_data) > 0:
            with open(save_path, "wb") as f:
                f.write(audio_data)
            os.chmod(save_path, 0o644)
            print(f"✅ [{role}] 音色合成成功：{save_path}")
            return True
        else:
            print(f"❌ [{role}] 未生成音频数据")
            if os.path.exists(save_path):
                os.remove(save_path)
            return False

    except Exception as e:
        print(f"❌ [{role}] 调用失败：{str(e)[:300]}")
        # 清理无效文件
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except:
                pass
        return False


# ===================== 重构：语音生成+入队，不再直接播放 =====================
async def generate_tts_and_enqueue(text: str, role: str = "fairy"):
    """
    生成TTS音频文件并加入播放队列（不直接播放，解决音频重叠顶掉问题）
    """
    processing_count[0] += 1
    temp_audio_path = f"temp_{role}_{uuid.uuid4().hex[:8]}.mp3"

    try:
        gen_success = await tts_http_generate(text, temp_audio_path, role)
        if gen_success and os.path.exists(temp_audio_path):
            # 将任务放入播放队列
            await play_queue.put((temp_audio_path, role, text))
            print(f"📥 [{role}] 已加入播放队列：{text[:30]}...")
        else:
            print(f"❌ [{role}] TTS生成失败，不加入队列：{text}")
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
    except Exception as e:
        print(f"❌ [{role}] 生成音频异常：{e}")
    finally:
        processing_count[0] -= 1


def pick_random_scan_audio() -> Optional[str]:
    """从扫码语录目录中随机挑选一个 mp3 文件"""
    if not os.path.exists(SCAN_AUDIO_DIR):
        return None
    files = [f for f in os.listdir(SCAN_AUDIO_DIR) if f.lower().endswith(".mp3")]
    if not files:
        return None
    return os.path.join(SCAN_AUDIO_DIR, random.choice(files))

# ===================== 扫码语录循环协程 =====================
async def scan_audio_loop():
    """每30秒随机播放扫码语录目录下的MP3，空格暂停冻结计时，Z键不影响，TTS来时自动礼让"""
    global tts_active, scan_paused

    if not os.path.exists(SCAN_AUDIO_DIR):
        print(f"❌ 找不到扫码语录目录：{SCAN_AUDIO_DIR}")
        return

    # 预扫描一次目录，确认有文件
    sample = pick_random_scan_audio()
    if not sample:
        print(f"⚠️ 扫码语录目录中没有 .mp3 文件：{SCAN_AUDIO_DIR}")
        return

    print(f"🔊 扫码语录随机播放已启动（目录：{SCAN_AUDIO_DIR}，间隔{SCAN_INTERVAL}秒）")
    clock = pygame.time.Clock()
    accumulated = 0
    interval_ms = SCAN_INTERVAL * 1000

    while True:
        dt = clock.tick(30)

        # 只有未被人为暂停（空格）时才累加计时器
        if not scan_paused:
            accumulated += dt

            # 到达触发时间点
            if accumulated >= interval_ms:
                if tts_active:
                    # TTS正在播放，本次顺延
                    accumulated = interval_ms
                else:
                    audio_file = pick_random_scan_audio()
                    if audio_file:
                        try:
                            pygame.mixer.music.load(audio_file)
                            pygame.mixer.music.play()
                            print(f"🔊 扫码语录播放中：{os.path.basename(audio_file)}")
                            accumulated = 0
                        except Exception as e:
                            print(f"❌ 扫码语录播放异常：{e}")
                            accumulated = 0
                    else:
                        print("⚠️ 未找到可用的扫码语录文件")
                        accumulated = 0

            # 如果正在播放扫码语录，实时检测TTS插入
            if pygame.mixer.music.get_busy():
                if tts_active:
                    pygame.mixer.music.pause()
                    print("⏸️ 扫码语录被TTS暂停（礼让）")
                    # 等待TTS全部结束
                    while tts_active:
                        await asyncio.sleep(0.1)
                    # TTS结束后，如果用户没按空格暂停，等10秒再恢复
                    if not scan_paused:
                        print(f"⏳ TTS结束，{SCAN_RESUME_DELAY}秒后恢复扫码语录...")
                        await asyncio.sleep(SCAN_RESUME_DELAY)
                        pygame.mixer.music.unpause()
                        print("▶️ 扫码语录恢复播放")
                    else:
                        print("⏸️ TTS结束，但扫码语录处于手动暂停状态，不自动恢复")

        await asyncio.sleep(0.01)


# ===================== 音频播放队列消费协程 =====================
async def audio_play_worker():
    """TTS播放队列（Z键控制暂停，与扫码语录互不影响但不能同时播放）"""
    global is_playing_queue, tts_active
    is_playing_queue = True
    print("🎵 TTS播放队列已启动（Z键暂停/继续，与扫码语录隔离）")

    while True:
        try:
            temp_audio_path, role, text = await play_queue.get()
            tts_active = True

            # 如果扫码语录正在播放，暂停它（不能同时播放）
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.pause()
                print("⏸️ 扫码语录因TTS开始而暂停")

            try:
                sound = pygame.mixer.Sound(temp_audio_path)
                channel = sound.play()
                if channel:
                    print(f"▶️ [{role.upper()}] 开始播放：{text[:50]}...")
                    while channel.get_busy():
                        # 检测Z键暂停（只影响TTS，不影响扫码语录）
                        if tts_paused:
                            pygame.mixer.pause()
                            while tts_paused:
                                await asyncio.sleep(0.1)
                            pygame.mixer.unpause()
                        await asyncio.sleep(0.1)
                    print(f"✅ [{role.upper()}] 播放完成：{text[:50]}...")
                else:
                    print(f"❌ [{role}] 音频通道分配失败")
            except Exception as e:
                print(f"❌ [{role}] 播放异常：{e}")
            finally:
                played_temp_files.add(temp_audio_path)
                play_queue.task_done()

                # 延迟判断队列是否空了
                await asyncio.sleep(0.3)
                if play_queue.qsize() == 0:
                    print(f"⏳ TTS队列空闲，{SCAN_RESUME_DELAY}秒后恢复扫码语录...")
                    await asyncio.sleep(SCAN_RESUME_DELAY)
                    tts_active = False
                    # 只有用户没按空格暂停扫码语录时才恢复
                    if not scan_paused:
                        try:
                            pygame.mixer.music.unpause()
                            print("▶️ 扫码语录恢复（TTS礼让结束）")
                        except Exception:
                            pass
                    else:
                        print("⏸️ 扫码语录保持手动暂停状态")
                # 队列还有任务则继续播下一条，tts_active保持True

        except Exception as e:
            print(f"❌ 播放队列异常：{e}")
            tts_active = False
            try:
                play_queue.task_done()
            except:
                pass
            await asyncio.sleep(1)


# ===================== 临时文件清理 =====================
async def clean_temp_files():
    """定期清理已播放的临时音频文件"""
    while True:
        await asyncio.sleep(30)  # 每30秒清理一次
        if not played_temp_files:
            continue

        deleted_count = 0
        for file_path in list(played_temp_files):
            try:
                if os.path.exists(file_path):
                    if os.name == "nt":
                        import ctypes

                        ctypes.windll.kernel32.DeleteFileW(file_path)
                    else:
                        os.remove(file_path)
                    deleted_count += 1
                played_temp_files.remove(file_path)
            except Exception as e:
                print(f"⚠️ 清理临时文件失败 {file_path}：{e}")

        if deleted_count > 0:
            print(f"🗑️ 清理了{deleted_count}个已播放的临时音频文件")


# ===================== 新增：键盘监听协程 =====================
async def keyboard_listener():
    """后台监听键盘：空格=扫码语录 | Z=TTS，两者完全隔离"""
    global scan_paused, tts_paused
    pygame.display.init()
    screen = pygame.display.set_mode((400, 100))
    pygame.display.set_caption("语音控制 - 空格=扫码语录 | Z=TTS")
    print("⌨️ 键盘监听已启动：【空格】暂停/继续扫码语录 | 【Z】暂停/继续TTS")

    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN:
                # 空格键：只控制扫码语录
                if event.key == pygame.K_SPACE:
                    scan_paused = not scan_paused
                    if scan_paused:
                        pygame.mixer.music.pause()
                        print("⏸️ 扫码语录已手动暂停（倒计时冻结）")
                    else:
                        # 只有TTS没活跃时才真正恢复播放
                        if not tts_active:
                            pygame.mixer.music.unpause()
                            print("▶️ 扫码语录已继续")
                        else:
                            print("▶️ 扫码语录待恢复（当前TTS占用中）")
                
                # Z键：只控制TTS（Sound通道）
                elif event.key == pygame.K_z:
                    tts_paused = not tts_paused
                    if tts_paused:
                        pygame.mixer.pause()
                        print("⏸️ TTS已手动暂停")
                    else:
                        pygame.mixer.unpause()
                        print("▶️ TTS已继续")
        clock.tick(30)
        await asyncio.sleep(0.01)


# ================================== ModelScope API调用 ==================================
def get_modelscope_reply(message_text, system_prompt, max_retries=3):
    """
    适配Qwen3-32B的ModelScope回复生成函数
    :param message_text: 用户输入文本
    :param system_prompt: 角色设定提示词
    :param max_retries: 重试次数
    :return: 模型回复文本
    """
    default_reply = (
        "主人，我有点没听清你说的是什么呢～"
        if "Fairy" in system_prompt
        else "哎呀没听清，再说一遍嘛😜"
    )

    for attempt in range(max_retries):
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message_text},
            ]

            response = modelscope_client.chat.completions.create(
                model=MODELSCOPE_MODEL_ID,
                messages=messages,
                max_tokens=QWEN_CONFIG["max_tokens"],
                temperature=QWEN_CONFIG["temperature"],
                top_p=QWEN_CONFIG["top_p"],
                presence_penalty=QWEN_CONFIG["presence_penalty"],
                frequency_penalty=QWEN_CONFIG["frequency_penalty"],
                stop=QWEN_CONFIG["stop"],
                stream=False,
            )

            if (
                response is None
                or not hasattr(response, "choices")
                or response.choices is None
                or len(response.choices) == 0
            ):
                print(f"⚠️ 第{attempt+1}次调用响应异常 - response: {response}")
                time.sleep(1)
                continue

            choice = response.choices[0]
            if (
                not hasattr(choice, "message")
                or choice.message is None
                or not choice.message.content
            ):
                print(f"⚠️ 第{attempt+1}次调用无有效内容 - choice: {choice}")
                time.sleep(1)
                continue

            reply_content = choice.message.content.strip()[:MAX_REPLY_LENGTH]
            return reply_content if reply_content else default_reply

        except RateLimitError as e:
            print(f"❌ Qwen3-32B限流（第{attempt+1}次）：{str(e)[:100]}")
            time.sleep(2)
        except AuthenticationError as e:
            print(f"❌ 认证失败（请检查MODELSCOPE_ACCESS_TOKEN）：{str(e)[:100]}")
            break
        except APIConnectionError as e:
            print(f"❌ 连接失败（第{attempt+1}次）：{str(e)[:100]}")
            time.sleep(1.5)
        except APIError as e:
            print(f"❌ 模型推理错误（第{attempt+1}次）：{str(e)[:100]}")
            if "model_not_found" in str(e):
                print(f"⚠️ 模型ID错误，请确认：{MODELSCOPE_MODEL_ID}")
                break
            time.sleep(1)
        except Exception as e:
            print(f"❌ 非流式调用失败（第{attempt+1}次）：{str(e)[:100]}")
            if attempt < max_retries - 1:
                time.sleep(1)

    print(f"❌ 所有重试均失败，用户输入：{message_text[:20]}...")
    return default_reply


# 封装Fairy/Youkai回复函数
def get_fairy_reply(message_text, msg_type="弹幕"):
    """Fairy角色回复生成"""
    prompt = f"【{msg_type}消息】{message_text}"
    return get_modelscope_reply(prompt, FAIRY_SYSTEM_PROMPT)


def get_youkai_reply(message_text, msg_type="弹幕"):
    """Youkai角色回复生成"""
    prompt = f"【{msg_type}消息】{message_text}"
    return get_modelscope_reply(prompt, YOUKAI_SYSTEM_PROMPT)


# ================================== 日志监控函数 ==================================
async def monitor_log_file(file_path, keywords, log_type):
    global last_danmu_reply_time

    def read_line(f):
        line = f.readline()
        if not line:
            return None
        return parse_line_content(line)

    if not os.path.exists(file_path):
        print(f"❌ [{log_type}] 找不到日志文件：{file_path}")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.seek(0, 2)
            print(f"✅ [{log_type}] 开始监控：{file_path}")

            if log_type == "弹幕":
                print(f"🔍 [{log_type}] Fairy触发关键词：{FAIRY_DANMU_KEYWORDS}")
                print(f"🔍 [{log_type}] Youkai触发关键词：{YOUKAI_DANMU_KEYWORDS}")
                print(
                    f"🔍 [{log_type}] 固定触发关键词：{[kw for cfg in FIXED_REPLY_CONFIG.values() for kw in cfg['keywords']]}"
                )
            else:
                print(f"🔍 [{log_type}] 无需关键词，所有有效消息均触发Fairy回复")

            while True:
                user_name = None
                # 弹幕专用解析
                if log_type == "弹幕":
                    user_name, content = parse_danmu(f.readline())
                    if not content:
                        await asyncio.sleep(0.5)
                        continue
                else:
                    content = read_line(f)
                    if not content:
                        await asyncio.sleep(0.5)
                        continue
                    user_name = "绳匠" if log_type == "礼物" else "未知"

                # 清洗性别和礼物标签
                content = remove_gender_tag(content)
                if log_type == "礼物":
                    content = remove_gift_combo_tag(content)

                # 发言统计 + 梯度感谢
                if log_type == "弹幕":
                    if user_name and user_name != "未知":
                        user_msg_count[user_name] += 1
                        cur_cnt = user_msg_count[user_name]
                        # 逐个检查里程碑
                        for thresh in THANK_THRESHOLDS:
                            if (
                                cur_cnt == thresh
                                and thresh not in thanked_thresholds[user_name]
                            ):
                                thanked_thresholds[user_name].add(thresh)
                                # 随机选择感谢风格（用 thresh 替换固定数字）
                                thank_styles = [
                                    f"绳匠 {user_name} 今天在直播间已经发言 {thresh} 次。请直接回复感谢语，无需复述问题，禁止出现问句。请用傲娇毒舌的语气感谢他，可顺便嘲讽主人或邦布来衬托他的积极。",
                                    f"绳匠 {user_name} 今天已发言 {thresh} 次，非常捧场。请直接回复感谢语，无需复述问题，禁止出现问句。请用嘴硬心软的方式感谢他，嘴上嫌弃话多，实际欣慰有人撑场子。",
                                    f"绳匠 {user_name} 今天发言 {thresh} 次。请直接回复感谢语，无需复述问题，禁止出现问句。请用冷静分析的语气表扬他，说他目前的活跃度已经超过主人本周的翻车次数。",
                                    f"绳匠 {user_name} 今天互动了 {thresh} 次。请直接回复感谢语，无需复述问题，禁止出现问句。请用假装不耐烦的语气感谢他，但暗地里给他的活跃档案加了一颗星。",
                                    f"绳匠 {user_name} 今天在直播间发言 {thresh} 次。请直接回复感谢语，无需复述问题，禁止出现问句。请用统计报告的方式感谢他，把他的活跃数据和主人挂机时长做个对比。",
                                ]
                                thank_prompt = random.choice(thank_styles)
                                async with api_lock:
                                    thank_text = get_fairy_reply(
                                        thank_prompt, "感谢活跃用户"
                                    )
                                if thank_text:
                                    print(
                                        f"🌟 活跃用户感谢（{thresh}次）：{thank_text}"
                                    )
                                    await generate_tts_and_enqueue(thank_text, "fairy")
                                    add_memory(
                                        user_name, f"发言{thresh}次达成", thank_text
                                    )
                                break  # 一次只触发一个里程碑，避免叠加

                # 固定关键词回复逻辑（保持不变，但下面的 continue 不会影响统计）
                if log_type == "弹幕":
                    fixed_reply = None
                    fixed_role = None
                    for key, config in FIXED_REPLY_CONFIG.items():
                        if any(kw in content for kw in config["keywords"]):
                            reply_data = config["reply_text"]
                            if isinstance(reply_data, list):
                                fixed_reply = random.choice(reply_data)
                            else:
                                fixed_reply = reply_data
                            fixed_role = config["role"]
                            break

                    if fixed_reply:
                        now = time.time()
                        if now - last_danmu_reply_time < DANMU_REPLY_INTERVAL:
                            print(
                                f"⏱️ [{log_type}] 距上次回复不足{DANMU_REPLY_INTERVAL}秒，跳过固定回复：{content[:20]}..."
                            )
                            continue
                        last_danmu_reply_time = now

                        print(f"\n💬 [{log_type}] 触发固定关键词回复：{content}")
                        print(
                            f"🧚 [{log_type}] {fixed_role.upper()}固定回复：{fixed_reply}"
                        )
                        # 播放预录制语音（优先本地文件，缺失则TTS）
                        keyword_folder = rf"E:\liveTools\Fairy\语录\关键词\{key}"
                        await play_local_or_tts(keyword_folder, fixed_role, fixed_reply)
                        continue

                # 普通弹幕/礼物回复逻辑（保持判断 trigger_role、冷却等不变）
                if log_type == "弹幕":
                    trigger_role = None
                    if any(keyword in content for keyword in YOUKAI_DANMU_KEYWORDS):
                        trigger_role = "youkai"
                    elif any(keyword in content for keyword in FAIRY_DANMU_KEYWORDS):
                        trigger_role = "fairy"
                    if not trigger_role:
                        continue

                    now = time.time()
                    if now - last_danmu_reply_time < DANMU_REPLY_INTERVAL:
                        print(
                            f"⏱️ [{log_type}] 距上次回复不足{DANMU_REPLY_INTERVAL}秒，跳过：{content[:20]}..."
                        )
                        continue
                    last_danmu_reply_time = now

                print(f"\n💬 [{log_type}] 收到消息：{content}")

                # 构建情景前缀
                prefix = build_common_prefix(log_type)

                # 生成回复（弹幕/礼物分支保持不变，但电量充电和记忆部分使用 user_name）
                if log_type == "弹幕":
                    # 构建背景信息块（与弹幕内容严格隔离）
                    bg_block = (
                        f"【系统提供的参考背景，请勿直接回应】\n{prefix}\n"
                        if prefix
                        else ""
                    )
                    question_block = f"【必须回复的弹幕消息】\n{content}"
                    enhanced_msg = bg_block + question_block
                    async with api_lock:
                        if trigger_role == "fairy":
                            reply_text = get_fairy_reply(enhanced_msg, log_type)
                            role = "fairy"
                        else:
                            reply_text = get_youkai_reply(enhanced_msg, log_type)
                            role = "youkai"
                else:
                    # 礼物消息原样保留
                    mood_list = [
                        "请用略带嫌弃的傲娇语气感谢，但要让人听出你其实很开心。",
                        "请假装正经地进行战术分析式感谢，把礼物比喻成战斗资源。",
                        "请用抱怨电费的方式拐弯感谢，最后补一句‘不过还是谢谢’。",
                        "请先吐槽主人刚犯的错，再顺便感谢礼物，体现傲娇本质。",
                        "请突然提到伊埃斯或邦布，把感谢说成是‘为了不让邦布啃线’才收下的。",
                    ]
                    extra_instruction = (
                        random.choice(mood_list)
                        + " 注意：这次感谢必须和你以往所有感谢语句完全不同，禁止雷同。"
                    )
                    enhanced_msg = f"{prefix}\n【{log_type}消息】{content}\n【附加要求】{extra_instruction}"
                    async with api_lock:
                        reply_text = get_fairy_reply(enhanced_msg, log_type)
                        role = "fairy"

                # 记忆存储（使用真实 user_name）
                if reply_text and role == "fairy":
                    add_memory(user_name if user_name else "绳匠", content, reply_text)

                if reply_text:
                    print(f"🧚 [{log_type}] {role.upper()}回复：{reply_text}")
                    await generate_tts_and_enqueue(reply_text, role)

    except UnicodeDecodeError:
        print(f"⚠️ [{log_type}] UTF-8编码失败，自动切换GBK编码...")
        with open(file_path, "r", encoding="gbk") as f:
            f.seek(0, 2)
            while True:
                user_name = None
                # 弹幕专用解析
                if log_type == "弹幕":
                    user_name, content = parse_danmu(f.readline())
                    if not content:
                        await asyncio.sleep(0.5)
                        continue
                else:
                    content = read_line(f)
                    if not content:
                        await asyncio.sleep(0.5)
                        continue
                    user_name = "绳匠" if log_type == "礼物" else "未知"

                # 清洗性别和礼物标签
                content = remove_gender_tag(content)
                if log_type == "礼物":
                    content = remove_gift_combo_tag(content)

                # 发言统计 + 梯度感谢
                if log_type == "弹幕":
                    if user_name and user_name != "未知":
                        user_msg_count[user_name] += 1
                        cur_cnt = user_msg_count[user_name]
                        # 逐个检查里程碑
                        for thresh in THANK_THRESHOLDS:
                            if (
                                cur_cnt == thresh
                                and thresh not in thanked_thresholds[user_name]
                            ):
                                thanked_thresholds[user_name].add(thresh)
                                # 随机选择感谢风格（用 thresh 替换固定数字）
                                thank_styles = [
                                    f"绳匠 {user_name} 今天在直播间已经发言 {thresh} 次。请直接回复感谢语，无需复述问题，禁止出现问句。请用傲娇毒舌的语气感谢他，可顺便嘲讽主人或邦布来衬托他的积极。",
                                    f"绳匠 {user_name} 今天已发言 {thresh} 次，非常捧场。请直接回复感谢语，无需复述问题，禁止出现问句。请用嘴硬心软的方式感谢他，嘴上嫌弃话多，实际欣慰有人撑场子。",
                                    f"绳匠 {user_name} 今天发言 {thresh} 次。请直接回复感谢语，无需复述问题，禁止出现问句。请用冷静分析的语气表扬他，说他目前的活跃度已经超过主人本周的翻车次数。",
                                    f"绳匠 {user_name} 今天互动了 {thresh} 次。请直接回复感谢语，无需复述问题，禁止出现问句。请用假装不耐烦的语气感谢他，但暗地里给他的活跃档案加了一颗星。",
                                    f"绳匠 {user_name} 今天在直播间发言 {thresh} 次。请直接回复感谢语，无需复述问题，禁止出现问句。请用统计报告的方式感谢他，把他的活跃数据和主人挂机时长做个对比。",
                                ]
                                thank_prompt = random.choice(thank_styles)
                                async with api_lock:
                                    thank_text = get_fairy_reply(
                                        thank_prompt, "感谢活跃用户"
                                    )
                                if thank_text:
                                    print(
                                        f"🌟 活跃用户感谢（{thresh}次）：{thank_text}"
                                    )
                                    await generate_tts_and_enqueue(thank_text, "fairy")
                                    add_memory(
                                        user_name, f"发言{thresh}次达成", thank_text
                                    )
                                break  # 一次只触发一个里程碑，避免叠加

                # 固定关键词回复逻辑（保持不变，但下面的 continue 不会影响统计）
                if log_type == "弹幕":
                    fixed_reply = None
                    fixed_role = None
                    for key, config in FIXED_REPLY_CONFIG.items():
                        if any(kw in content for kw in config["keywords"]):
                            reply_data = config["reply_text"]
                            if isinstance(reply_data, list):
                                fixed_reply = random.choice(reply_data)
                            else:
                                fixed_reply = reply_data
                            fixed_role = config["role"]
                        break

                    if fixed_reply:
                        now = time.time()
                        if now - last_danmu_reply_time < DANMU_REPLY_INTERVAL:
                            print(
                                f"⏱️ [{log_type}] 距上次回复不足{DANMU_REPLY_INTERVAL}秒，跳过固定回复：{content[:20]}..."
                            )
                            continue
                        last_danmu_reply_time = now

                        print(f"\n💬 [{log_type}] 触发固定关键词回复：{content}")
                        print(
                            f"🧚 [{log_type}] {fixed_role.upper()}固定回复：{fixed_reply}"
                        )
                        # 播放预录制语音（优先本地文件，缺失则TTS）
                        keyword_folder = rf"E:\liveTools\Fairy\语录\关键词\{key}"
                        await play_local_or_tts(keyword_folder, fixed_role, fixed_reply)
                        continue

                # 普通弹幕/礼物回复逻辑（保持判断 trigger_role、冷却等不变）
                if log_type == "弹幕":
                    trigger_role = None
                    if any(keyword in content for keyword in YOUKAI_DANMU_KEYWORDS):
                        trigger_role = "youkai"
                    elif any(keyword in content for keyword in FAIRY_DANMU_KEYWORDS):
                        trigger_role = "fairy"
                    if not trigger_role:
                        continue

                    now = time.time()
                    if now - last_danmu_reply_time < DANMU_REPLY_INTERVAL:
                        print(
                            f"⏱️ [{log_type}] 距上次回复不足{DANMU_REPLY_INTERVAL}秒，跳过：{content[:20]}..."
                        )
                        continue
                    last_danmu_reply_time = now

                print(f"\n💬 [{log_type}] 收到消息：{content}")

                # 构建情景前缀
                prefix = build_common_prefix(log_type)

                # 生成回复（弹幕/礼物分支保持不变，但电量充电和记忆部分使用 user_name）
                if log_type == "弹幕":
                    # 构建背景信息块（与弹幕内容严格隔离）
                    bg_block = (
                        f"【系统提供的参考背景，请勿直接回应】\n{prefix}\n"
                        if prefix
                        else ""
                    )
                    question_block = f"【必须回复的弹幕消息】\n{content}"
                    enhanced_msg = bg_block + question_block
                    async with api_lock:
                        if trigger_role == "fairy":
                            reply_text = get_fairy_reply(enhanced_msg, log_type)
                            role = "fairy"
                        else:
                            reply_text = get_youkai_reply(enhanced_msg, log_type)
                            role = "youkai"
                else:
                    # 礼物消息原样保留
                    mood_list = [
                        "请用略带嫌弃的傲娇语气感谢，但要让人听出你其实很开心。",
                        "请假装正经地进行战术分析式感谢，把礼物比喻成战斗资源。",
                        "请用抱怨电费的方式拐弯感谢，最后补一句‘不过还是谢谢’。",
                        "请先吐槽主人刚犯的错，再顺便感谢礼物，体现傲娇本质。",
                        "请突然提到伊埃斯或邦布，把感谢说成是‘为了不让邦布啃线’才收下的。",
                    ]
                    extra_instruction = (
                        random.choice(mood_list)
                        + " 注意：这次感谢必须和你以往所有感谢语句完全不同，禁止雷同。"
                    )
                    enhanced_msg = f"{prefix}\n【{log_type}消息】{content}\n【附加要求】{extra_instruction}"
                    async with api_lock:
                        reply_text = get_fairy_reply(enhanced_msg, log_type)
                        role = "fairy"

                # 记忆存储（使用真实 user_name）
                if reply_text and role == "fairy":
                    add_memory(user_name if user_name else "绳匠", content, reply_text)

                if reply_text:
                    print(f"🧚 [{log_type}] {role.upper()}回复：{reply_text}")
                    await generate_tts_and_enqueue(reply_text, role)


# ================================== 进直播间监控 ==================================
async def monitor_enter_room_file(file_path):
    global last_welcome_user
    log_type = "进直播间"

    def read_line(f):
        line = f.readline()
        if not line:
            return None
        return line.strip()

    if not os.path.exists(file_path):
        print(f"❌ [{log_type}] 找不到日志文件：{file_path}")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.seek(0, 2)
            print(f"✅ [{log_type}] 开始监控：{file_path}")
            print(f"🔍 [{log_type}] 欢迎用户列表：{WELCOME_USERS}")
            print(f"⏱️ [{log_type}] 同一用户欢迎冷却：{ENTER_ROOM_WELCOME_INTERVAL}秒")

            while True:
                line = read_line(f)
                if not line:
                    await asyncio.sleep(0.5)
                    continue

                user_name = parse_enter_room_content(line)
                if not user_name or user_name not in WELCOME_USERS:
                    continue

                now = time.time()
                if (
                    user_name in last_welcome_user
                    and now - last_welcome_user[user_name] < ENTER_ROOM_WELCOME_INTERVAL
                ):
                    print(f"⏱️ [{log_type}] {user_name} 冷却中，跳过欢迎")
                    continue
                last_welcome_user[user_name] = now

                print(f"\n👋 [{log_type}] 检测到指定用户进入：{user_name}")
                prefix = build_common_prefix("欢迎")
                welcome_prompt = (
                    f"{prefix}\nfairy，高级粉丝团成员{user_name}进入直播间，快欢迎！"
                )
                async with api_lock:
                    reply_text = get_fairy_reply(welcome_prompt, log_type)

                if reply_text:
                    print(f"🧚 [{log_type}] Fairy欢迎：{reply_text}")
                    await generate_tts_and_enqueue(reply_text, role="fairy")

    except UnicodeDecodeError:
        print(f"⚠️ [{log_type}] UTF-8编码失败，自动切换GBK编码...")
        with open(file_path, "r", encoding="gbk") as f:
            f.seek(0, 2)
            while True:
                line = read_line(f)
                if not line:
                    await asyncio.sleep(0.5)
                    continue

                user_name = parse_enter_room_content(line)
                if not user_name or user_name not in WELCOME_USERS:
                    continue

                now = time.time()
                if (
                    user_name in last_welcome_user
                    and now - last_welcome_user[user_name] < ENTER_ROOM_WELCOME_INTERVAL
                ):
                    continue
                last_welcome_user[user_name] = now

                print(f"\n👋 [{log_type}] 检测到指定用户进入：{user_name}")
                prefix = build_common_prefix("欢迎")
                welcome_prompt = (
                    f"{prefix}\nfairy，高级粉丝团成员{user_name}进入直播间，快欢迎！"
                )
                async with api_lock:
                    reply_text = get_fairy_reply(welcome_prompt, log_type)

                if reply_text:
                    print(f"🧚 [{log_type}] Fairy欢迎：{reply_text}")
                    await generate_tts_and_enqueue(reply_text, role="fairy")


# ================================== 定时对话函数 ==================================
async def run_chat_round():
    try:
        # 按权重决定对话类型：独白 90%，fairy_to_youkai 5%，youkai_to_fairy 5%
        r = random.random()
        if r < 0.9:
            # Fairy 独白：直接从语录库中选择
            monologue_text = get_random_monologue()
            print(f"🧚 Fairy（独白）：{monologue_text}")
            await play_local_or_tts(r"E:\liveTools\Fairy\语录\独白", "fairy", monologue_text)
        elif r < 0.95:
            # Fairy 对 Youkai（发起句优先本地音频，Youkai 回复仍由 AI 生成）
            init_quote = get_interaction_quote("fairy_to_youkai")
            print(f"🧚 Fairy（发起）：{init_quote}")
            await play_local_or_tts(r"E:\liveTools\Fairy\语录\FairyToYoukai", "fairy", init_quote)
            await asyncio.sleep(1)
            async with api_lock:
                youkai_reply = get_youkai_reply(init_quote, msg_type="闲聊")
            if youkai_reply:
                print(f"👻 Youkai（回复）：{youkai_reply}")
                await generate_tts_and_enqueue(youkai_reply, "youkai")
        else:
            # Youkai 对 Fairy（发起句优先本地音频，Fairy 回复仍由 AI 生成）
            init_quote = get_interaction_quote("youkai_to_fairy")
            print(f"👻 Youkai（发起）：{init_quote}")
            await play_local_or_tts(r"E:\liveTools\Youkai\语录\YoukaiToFairy", "youkai", init_quote)
            await asyncio.sleep(1)
            async with api_lock:
                fairy_reply = get_fairy_reply(init_quote, msg_type="闲聊")
            if fairy_reply:
                print(f"🧚 Fairy（回复）：{fairy_reply}")
                await generate_tts_and_enqueue(fairy_reply, "fairy")
    except Exception as e:
        print(f"❌ 定时对话执行异常：{e}")


async def scheduled_chat_task():
    if not ENABLE_SCHEDULED_CHAT:
        print("⏸️ 定时对话已禁用")
        return

    print(
        f"✅ 定时对话启动（基础间隔{CHAT_BASE_INTERVAL}秒，随机偏移±{CHAT_RANDOM_OFFSET}秒）"
    )
    print(f"📊 对话概率分配：Fairy独白 90% | Fairy→Youkai 5% | Youkai→Fairy 5%")

    while True:
        try:
            chat_interval = max(60, get_random_chat_interval())
            print(f"\n⏳ 下次定时对话将在 {chat_interval} 秒后触发")
            await asyncio.sleep(chat_interval)

            # 队列中有任务时跳过（避免叠加）
            if play_queue.qsize() > 0:
                print(f"⚠️ 播放队列已有{play_queue.qsize()}个任务，跳过本次定时对话")
                continue

            await run_chat_round()
        except Exception as e:
            print(f"❌ 定时对话任务异常：{e}")
            continue


# ================================== 主函数 ==================================
async def main():
    print("🎮 绝区零Fairy&Youkai直播助手（ModelScope官方版）已启动")
    print(f"🔗 ModelScope Base URL：{MODELSCOPE_BASE_URL}")
    print(f"🔗 ModelScope使用模型：{MODELSCOPE_MODEL_ID}")
    print(f"🔗 代理配置：{PROXY_SETTINGS}")
    print("=" * 60)

    # 初始化pygame混音器（设置多通道）
    pygame.mixer.init(channels=8)  # 8个音频通道，足够应对直播场景

    # 启动播放队列消费协程
    asyncio.create_task(audio_play_worker())
    # 启动临时文件清理协程
    asyncio.create_task(clean_temp_files())
    # 启动扫码语录循环协程（每30秒播放，TTS时自动暂停）
    asyncio.create_task(scan_audio_loop())
        # 启动键盘监听协程（空格键控制所有语音暂停/继续）
    asyncio.create_task(keyboard_listener())

    # 启动所有监控任务
    try:
        # 启动所有监控任务
        task1 = asyncio.create_task(monitor_log_file(DANMU_FILE_PATH, [], "弹幕"))
        task2 = asyncio.create_task(monitor_log_file(GIFT_FILE_PATH, [], "礼物"))
        task3 = asyncio.create_task(monitor_enter_room_file(ENTER_ROOM_FILE_PATH))
        task4 = asyncio.create_task(scheduled_chat_task())

        await asyncio.gather(task1, task2, task3, task4)
    except Exception as e:
        crash_info = (
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 闪退异常\n"
            f"错误类型: {type(e).__name__}\n"
            f"错误信息: {str(e)}\n"
            f"队列待处理: {play_queue.qsize()}\n"
            f"详细堆栈:\n{traceback.format_exc()}\n"
        )
        print(f"\n❌ 程序崩溃，正在写入日志到 {CRASH_LOG_FILE}")
        print(crash_info)
        try:
            os.makedirs(CRASH_LOG_DIR, exist_ok=True)
            with open(CRASH_LOG_FILE, "w", encoding="utf-8") as f:
                f.write(crash_info)
                f.flush()
            print(f"✅ 崩溃日志已保存至 {CRASH_LOG_FILE}")
        except Exception as log_err:
            print(f"❌ 写入崩溃日志失败: {log_err}")
            # 无论如何，强行打印到控制台
            print(crash_info)
        raise  # 保持退出行为


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 程序被用户中断")
        # 等待播放队列处理完成
        print(f"⏳ 等待播放队列剩余{play_queue.qsize()}个任务完成...")
        # 注意：asyncio.run 之外不能再嵌套 asyncio.run，直接退出
        # 事件循环已关闭，不再调用 asyncio.all_tasks()
        pass
    except Exception as e:
        print(f"\n❌ 程序异常退出：{e}")
        import traceback

        traceback.print_exc()
    finally:
        # 清理所有临时文件
        print("\n🗑️ 清理所有临时音频文件...")
        for file_path in played_temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
        # 清理未播放的临时文件（匹配temp_开头的mp3）
        for file in os.listdir("."):
            if file.startswith("temp_") and file.endswith(".mp3"):
                try:
                    os.remove(file)
                except:
                    pass
        try:
            pygame.mixer.quit()
        except:
            pass
        # ↓↓↓ 新增：关闭键盘监听窗口 ↓↓↓
        try:
            pygame.display.quit()
        except:
            pass
        # ↑↑↑ 新增结束 ↑↑↑
        print("✅ 程序已安全退出")
