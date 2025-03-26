import json
import random
import os
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("astrbot_plugin_idiom", "idiom", "成语接龙插件", "1.0.0")
class idiomPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.idiom_file = os.path.join(os.path.dirname(__file__), "idiom.json")  # 详细成语数据文件
        self.idioms = self.load_idioms()
        self.games = {}  # 维护多个游戏会话，每个用户或群聊有独立状态
    
    def load_idioms(self):
        """加载本地成语数据，并标准化格式，分批处理"""
        if not os.path.exists(self.idiom_file):
            logger.error(f"❌ 成语数据文件 '{self.idiom_file}' 不存在！请检查文件路径。")
            return {}
        try:
            with open(self.idiom_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {item["word"].strip(): item for item in data}  # 使用成语作为键
        except Exception as e:
            logger.error(f"❌ 读取成语数据失败: {e}")
            return {}
    
    def get_session_id(self, event: AstrMessageEvent):
        """获取会话ID，区分私聊和群聊"""
        return event.get_group_id() if event.get_group_id() else event.get_session_id()
    
    def get_game(self, session_id):
        """获取当前会话的游戏状态"""
        if session_id not in self.games:
            self.games[session_id] = {
                'used_idioms': set(),
                'last_idiom': None
            }
        return self.games[session_id]

    @filter.command("idiom")
    async def handle_idiom(self, event: AstrMessageEvent, user_idiom: str = ""):
        '''成语接龙游戏'''  # 指令描述
        session_id = self.get_session_id(event)
        game = self.get_game(session_id)

        user_idiom = user_idiom.strip().split('@')[0]  # 去除输入的空格以及@消息，防止匹配错误

        if not user_idiom:
            yield event.plain_result("用法: /idiom [成语]，例如 /idiom 一帆风顺")
            return

        if user_idiom == "结束":
            del self.games[session_id]
            yield event.plain_result("✅ 游戏已手动结束，欢迎下次再来！")
            return

        if user_idiom not in self.idioms:
            yield event.plain_result(f"❌ 这个成语 '{user_idiom}' 不存在，请换一个！")
            return

        if user_idiom in game['used_idioms']:
            yield event.plain_result("⚠️ 这个成语已经被用过了，请换一个！")
            return

        if game['last_idiom'] and user_idiom[0] != game['last_idiom'][-1]:
            yield event.plain_result(f"❌ 成语必须以 '{game['last_idiom'][-1]}' 开头！")
            return

        # 记录成语
        game['used_idioms'].add(user_idiom)
        game['last_idiom'] = user_idiom

        # 找到可以接龙的成语
        possible_next = [idiom for idiom in self.idioms if idiom[0] == user_idiom[-1] and idiom not in game['used_idioms']]
        if possible_next:
            bot_choice = random.choice(possible_next)
            game['used_idioms'].add(bot_choice)
            game['last_idiom'] = bot_choice
            yield event.plain_result(f"✅ {user_idiom} → {bot_choice}")
        else:
            yield event.plain_result(f"🎉 {user_idiom} 是最后一个可用成语，你赢了！游戏结束。")
            del self.games[session_id]

    @filter.command("idiom_info")
    async def handle_idiom_info(self, event: AstrMessageEvent, user_idiom: str = ""):
        '''查询成语信息'''  # 指令描述
        user_idiom = user_idiom.strip()
        if not user_idiom:
            yield event.plain_result("用法: /idiom_info [成语]，例如 /idiom_info 一帆风顺")
            return
        
        if user_idiom not in self.idioms:
            yield event.plain_result(f"❌ 这个成语 '{user_idiom}' 不存在，请换一个！")
            return

        info = self.idioms[user_idiom]
        result = (f"📖 成语: {info['word']}\n"
                  f"🔤 拼音: {info['pinyin']}\n"
                  f"📝 释义: {info['explanation']}\n"
                  f"📚 出处: {info['derivation']}\n"
                  f"📌 例句: {info['example']}")
        yield event.plain_result(result)

    async def terminate(self):
        '''插件卸载/停用时执行的清理操作'''
        self.games.clear()
        logger.info("成语接龙插件已卸载")
