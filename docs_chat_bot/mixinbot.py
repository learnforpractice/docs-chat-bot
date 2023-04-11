# -*- coding: utf-8 -*-

import argparse
import asyncio
import base64
import pickle
import signal
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union

import httpx
import websockets
import yaml
from pymixin import log, utils
from pymixin.mixin_ws_api import MessageView, MixinWSApi

logger = log.get_logger(__name__)
logger.addHandler(log.handler)

@dataclass
class AnswerRequestTask:
    conversation_id: str
    user_id: str
    task: asyncio.Task

@dataclass
class SavedQuestion:
    conversation_id: str
    user_id: str
    data: str

sayhi = {
    'hi': '''
Hello, this is an Q&A robot about Python Smart Contracts Development. Is there anything I can help you with?
    ''',

    '你好': '''
你好，这是一个关于Python智能合约开发的问答机器人，请问有什么可以帮到你的吗？
    ''',

    'こんにちは': '''
こんにちは、これはPythonスマートコントラクト開発に関するQ&Aロボットです。何かお手伝いできることがありますか？
    '''
}

class MixinBot(MixinWSApi):
    def __init__(self, config_file):
        f = open(config_file)
        config = yaml.safe_load(f)
        super().__init__(config['bot_config'], on_message=self.on_message)
        self.openai_api_keys = config['openai_api_keys']

        with open(config['indexed_docs'], 'rb') as f:
            self.indexed_docs = pickle.load(f)

        self.client_id = config['bot_config']['client_id']

        self.tasks: List[SavedQuestion] = []
        self.saved_questions: Dict[str, SavedQuestion] = {}

        self.developer_conversation_id = None
        self.developer_user_id = None
        self.web_client = httpx.AsyncClient()

        if 'developer_conversation_id' in config:
            self.developer_conversation_id = config['developer_conversation_id']
            self.developer_user_id = config['developer_user_id']
        # openai_api_key
        self.bots = []
        self.standby_bots = []
        self._paused = False

    @property
    def paused(self):
        return self._paused
    
    @paused.setter
    def paused(self, value):
        self._paused = value

    async def init(self):
        asyncio.create_task(self.handle_questions())

        if self.openai_api_keys:
            from .chatgpt import ChatGPTBot
            for key in self.openai_api_keys:
                bot = ChatGPTBot(key, self.indexed_docs)
                await bot.init()
                self.bots.append(bot)
        
        assert self.bots

        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(self.handle_signal(signal.SIGINT)))
        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(self.handle_signal(signal.SIGTERM)))

    async def handle_signal(self, signum):
        logger.info("+++++++handle signal: %s", signum)
        for bot in self.bots:
            logger.info("++close bot: %s", bot)
            await bot.close()
        loop = asyncio.get_running_loop()
        loop.remove_signal_handler(signal.SIGINT)
        loop.remove_signal_handler(signal.SIGTERM)
        sys.exit(0)
        # os.kill(os.getpid(), signal.SIGINT)

    def choose_bot(self, user_id):
        bots = []
        for bot in self.bots:
            if bot.standby:
                continue
            bots.append(bot)

        for bot in bots:
            if user_id in bot.users:
                return bot

        bot_index = 0
        user_counts = [len(bot.users) for bot in bots]
        try:
            bot_index = user_counts.index(min(user_counts))
            return bots[bot_index]
        except ValueError:
            return None

    async def send_message_to_chat_gpt(self, conversation_id: str, user_id: str, message: str):
        bot = self.choose_bot(user_id)
        if not bot:
            logger.info('no available bot')
            self.save_question(conversation_id, user_id, message)
            #queue message
            return False
        try:
            async for msg in bot.send_message(user_id, message):
                await self.sendUserText(conversation_id, user_id, msg)
            await self.sendUserText(conversation_id, user_id, "[END]")
            return True
        except Exception as e:
            logger.exception(e)
        self.save_question(conversation_id, user_id, message)
        return False

    async def send_message_to_chat_gpt2(self, conversation_id, user_id, message):
        bot = self.choose_bot(user_id)
        if not bot:
            logger.info('no available bot')
            self.save_question(conversation_id, user_id, message)
            return False

        msgs: List[str] = []
        try:
            async for msg in bot.send_message(user_id, message):
                msgs.append(msg)
            await self.sendUserText(conversation_id, user_id, ''.join(msgs) + '\n[END]')
            return True
        except Exception as e:
            logger.exception(e)
        self.save_question(conversation_id, user_id, message)
        return False

    async def handle_questions(self):
        while True:
            await asyncio.sleep(15.0)
            handled_question = []
            saved_questions = self.saved_questions.copy()
            for user_id, question in saved_questions.items():
                try:
                    logger.info("++++++++handle question: %s", question.data)
                    if await self.send_message_to_chat_gpt2(question.conversation_id, question.user_id, question.data):
                        handled_question.append(user_id)
                except Exception as e:
                    logger.info("%s", str(e))
                    continue
            for question in handled_question:
                del self.saved_questions[question]

    def save_question(self, conversation_id, user_id, data):
        self.saved_questions[user_id] = SavedQuestion(conversation_id, user_id, data)

    async def handle_message(self, conversation_id, user_id, message):
        try:
            await self.send_message_to_chat_gpt(conversation_id, user_id, message)
        except Exception as e:
            logger.exception(e)
            if self.developer_user_id:
                await self.sendUserText(self.developer_conversation_id, self.developer_user_id, f"exception occur at:{time.time()}: {traceback.format_exc()}")

    async def handle_group_message(self, conversation_id, user_id, data):
        await self.send_message_to_chat_gpt2(conversation_id, user_id, data)

    async def on_message(self, id: str, action: str, msg: Optional[MessageView]):
        if action not in ["ACKNOWLEDGE_MESSAGE_RECEIPT", "CREATE_MESSAGE", "LIST_PENDING_MESSAGES"]:
            logger.info("unknow action %s", action)
            return

        if action == "ACKNOWLEDGE_MESSAGE_RECEIPT":
            return

        if not action == "CREATE_MESSAGE":
            return

        if not msg:
            return

        logger.info('++++++++conversation_id:%s', msg.conversation_id)

        await self.echoMessage(msg.message_id)

        logger.info('user_id %s', msg.user_id)
        logger.info("created_at %s",msg.created_at)

        if not msg.category in ["SYSTEM_ACCOUNT_SNAPSHOT", "PLAIN_TEXT", "SYSTEM_CONVERSATION", "PLAIN_STICKER", "PLAIN_IMAGE", "PLAIN_CONTACT"]:
            logger.info("unknown category: %s", msg.category)
            return

        if not msg.category == "PLAIN_TEXT" and msg.type == "message":
            return

        data = msg.data
        logger.info(data)
        data = base64.urlsafe_b64decode(data)

        if data.startswith(b'@'):
            index = data.find(b' ')
            if index == -1:
                return
            data = data[index + 1:]
        data = data.decode()
        logger.info(data)

        try:
            reply = sayhi[data]
            await self.sendUserText(msg.conversation_id, msg.user_id, reply)
            return
        except KeyError:
            pass

        if utils.unique_conversation_id(msg.user_id, self.client_id) == msg.conversation_id:
            asyncio.create_task(self.handle_message(msg.conversation_id, msg.user_id, data))
        else:
            asyncio.create_task(self.handle_group_message(msg.conversation_id, msg.user_id, data))

    async def run(self):
        try:
            while not self.paused:
                try:
                    await super().run()
                except websockets.exceptions.ConnectionClosedError as e:
                    logger.exception(e)
                    self.ws = None
                #asyncio.exceptions.TimeoutError
                except Exception as e:
                    logger.exception(e)
                    self.ws = None
        except asyncio.CancelledError:
            if self.ws:
                await self.ws.close()
            if self.web_client:
                await self.web_client.aclose()
            logger.info("mixin websocket was cancelled!")

    async def close(self):
        for bot in self.bots:
            await bot.close()

bot: Optional[MixinBot]  = None

def exception_handler(loop, context):
    # loop.default_exception_handler(context)
    logger.info("exception_handler: %s", context)
    loop.close()

async def start():
    global bot

    parser = argparse.ArgumentParser(description="Chat-bot")
    parser.add_argument('config_file')
    
    args = parser.parse_args()

    bot = MixinBot(args.config_file)
    await bot.init()
    asyncio.create_task(bot.run())
    print('started')
    while not bot.paused:
        await asyncio.sleep(1.0)

async def stop():
    global bot
    await bot.ws.close()

async def resume():
    global bot
    bot.paused = False
    while not bot.paused:
        await asyncio.sleep(1.0)

def run():
    asyncio.run(start())

if __name__ == '__main__':
    run()
