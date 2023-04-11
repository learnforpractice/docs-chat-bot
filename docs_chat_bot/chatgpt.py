import asyncio
import logging
import time
import uuid
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

import openai
import tiktoken

from .utils import count_tokens, get_embedding, top_n_similarity

logger = logging.getLogger(__name__)

max_prompt_token = 3000
rate_limit_size = 5
rate_limit_window_seconds = 60

gpt_encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

class RateLimitExceededError(Exception):
    pass

class ChatGPTBot:
    def __init__(self, api_key: str, embedding_docs, stream=True):
        openai.api_key = api_key

        self.standby = False
        self.users: Dict[str, bool] = {}

        self.lock = asyncio.Lock()
        self.stream = stream
        self.rate_limits: Dict[str, deque] = {}
        self.embedding_docs = embedding_docs

    async def init(self):
        pass

    async def close(self):
        pass

    def generate_prompt(self, conversation_id: str, question: str) -> Optional[List[Dict[str, str]]]:
        logger.info("+++++++question: %s", question)
        query_embedding = get_embedding(question)
        document_similarities = top_n_similarity(query_embedding, self.embedding_docs, 4)
        guide = """
I want you to act as an AI assistant, adept at analyzing provided text and answering questions based on the given context. When presented with extracted parts of a long document and a question, offer a conversational answer that is accurate and helpful. If the answer cannot be found within the provided context, simply respond with "Hmm, I'm not sure," without adding any speculative or extraneous information. Focus on delivering precise and reliable assistance based on the available information.
here are some rules to follow:
1. action name should be less than 12 characters, and only contain the following characters ".12345abcdefghijklmnopqrstuvwxyz"
for example:
```python
@action("hello")
def hello():
    print('hello')
```
"hello" is less then 12 characters, and only contains characters in ".12345abcdefghijklmnopqrstuvwxyz"
2. reply with the same language of the latest question.

context:
"""
        token_count = count_tokens(guide)

        tunks = []
        prompt = ''
        for similarity, document in document_similarities[:3]:
            logger.info("similarity: %s, document: %s", similarity, document[:20])
            if similarity > 0.5:
                tunks.append(document)
            content = '\n'.join(tunks)
            tmp_prompt = f'''
{guide}
###
{content}
###
Question: {question}
Answer:'''
            tokens_in_prompt = count_tokens(prompt)
            if token_count + tokens_in_prompt > max_prompt_token:
                break
            token_count += tokens_in_prompt
            prompt = tmp_prompt

        if not prompt:
            return "Sorry, prompt too long"

        context_messages = []
        context_messages.append({"role": "system", "content":  guide})
        context_messages.append({"role": "user", "content": prompt})
        return context_messages

    def check_rate_limit(self, conversation_id: str):
        try:
            request_timestamps = self.rate_limits[conversation_id]
        except KeyError:
            request_timestamps = deque(maxlen=rate_limit_size)
            self.rate_limits[conversation_id] = request_timestamps

        current_time = time.time()
        # Remove timestamps older than the window
        while request_timestamps and current_time - request_timestamps[0] > rate_limit_window_seconds:
            request_timestamps.popleft()

        # Check if the request limit has been reached
        if len(request_timestamps) >= rate_limit_size:
            raise RateLimitExceededError(f"Rate limit exceeded. You can make the next request after {request_timestamps[0] + rate_limit_window_seconds - current_time:.2f} seconds.")

        request_timestamps.append(current_time)

    async def send_message(self, conversation_id: str, message: str):
        try:
            self.check_rate_limit(conversation_id)
        except RateLimitExceededError as e:
            yield "[BEGIN]"
            yield str(e)
            return

        async with self.lock:
            if self.stream:
                async for msg in self._send_message_stream(conversation_id, message):
                    yield msg
            else:
                async for msg in self._send_message(conversation_id, message):
                    yield msg

    async def _send_message(self, conversation_id: str, message: str):
        if len(message) == 0:
            return
        self.users[conversation_id] = True

        prompt = self.generate_prompt(conversation_id, message)
        # logger.info('+++prompt:%s', prompt)
        if not prompt:
            yield '[BEGIN]'
            yield 'oops, something went wrong, please try to reduce your worlds.'
            return
        try:
            yield '[BEGIN]'
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=prompt
            )
        except openai.error.InvalidRequestError as e:
            logger.exception(e)
            yield 'Sorry, I am not available now.'
            return
        reply = response['choices'][0]['message']['content']
        logger.info('++++response: %s', reply)
        self.add_messsage(conversation_id, message, reply)
        yield reply
        return

    async def _send_message_stream(self, conversation_id: str, message: str):
        if len(message) == 0:
            return
        self.users[conversation_id] = True
        prompt = self.generate_prompt(conversation_id, message)
        if not prompt:
            yield '[BEGIN]'
            yield 'oops, something went wrong, please try to reduce your worlds.'
            return
        start_time = time.time()
        try:
            yield '[BEGIN]'
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=prompt,
                stream=True
            )
        except openai.error.InvalidRequestError as e:
            logger.exception(e)
            yield 'Sorry, I am not available now.'
            return
        collected_events = []
        completion_text = ''
        tokens: List[str] = []

        async for event in response:
            collected_events.append(event)  # save the event response
            # logger.info(event)
            delta = event['choices'][0]['delta']
            if not delta:
                break
            if not 'content' in delta:
                continue
            event_text = delta['content']  # extract the text
            tokens.append(event_text)
            if event_text.endswith('\n'):
                if time.time() - start_time > 3.0:
                    start_time = time.time()
                    reply = ''.join(tokens)
                    reply = reply.strip()
                    if reply:
                        yield reply
                    tokens = []
            completion_text += event_text  # append the text
        reply = completion_text
        logger.info('++++response: %s', reply)
        yield ''.join(tokens)
        return
