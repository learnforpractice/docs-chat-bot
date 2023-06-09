import argparse
import os
import pickle
import time

import numpy as np
import openai
import tiktoken
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

EMBEDDING_MODEL = "text-embedding-ada-002"
max_prompt_token = 3000

from pymixin import log

logger = log.get_logger(__name__)
logger.addHandler(log.handler)


gpt_encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

from .utils import count_tokens, get_embedding, top_n_similarity

embeddings = None

def query(question):
    global embeddings
    logger.info("+++++++question: %s", question)
    query_embedding = get_embedding(question)
    query_embedding = np.array(query_embedding)
    document_similarities = top_n_similarity(query_embedding, embeddings, 4)
    guide = """
I want you to act as an AI assistant, adept at analyzing provided text and answering questions based on the given context. When presented with extracted parts of a long document and a question, offer a conversational answer that is accurate and helpful. If the answer cannot be found within the provided context, simply respond with "Hmm, I'm not sure," without adding any speculative or extraneous information. Focus on delivering precise and reliable assistance based on the available information.
here are some rules to follow:
1. action name should be less than 12 characters, and only contain the following characters ".12345abcdefghijklmnopqrstuvwxyz"
for example:
```
@action("hello")
def hello():
    print('hello')
```
"hello" is less then 12 characters, and only contains characters in ".12345abcdefghijklmnopqrstuvwxyz"
2. reply with the same language of the latest question.
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
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=context_messages,
        timeout=30
    )
    ret = response['choices'][0]['message']['content']
    # logger.info("+++++++++ret: %s", ret)
    return ret

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can specify the allowed origins or use ["*"] to allow all
    allow_credentials=True,
    allow_methods=["*"],  # You can specify the allowed methods or use ["*"] to allow all
    allow_headers=["*"],  # You can specify the allowed headers or use ["*"] to allow all
)

class MessageInput(BaseModel):
    message: str

@app.post("/chat")
async def receive_message(data: MessageInput):
    message = data.message
    logger.info("message: %s", message)
    if len(message) > 1024:
        response = {
            "status": "error",
            "received_message": 'sorry, the message is too long'
        }
        return response
    try:
        ret = query(message)
        response = {
            "status": "success",
            "received_message": ret
        }
        return response
    except Exception as e:
        logger.exception(e)
    return 'oops!'

def main():
    global embeddings
    import uvicorn
    parser = argparse.ArgumentParser(description="Chat-bot server")
    parser.add_argument(
        "--host",
        type=str,
        default='127.0.0.1',
        help="The host IP address for the chat-bot server, default to 127.0.0.1"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=7999,
        help="The port number for the chat-bot server, default to 7999"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default='',
        help="The openai api key or use the environment variable 'openai_api_key'"
    )
    
    parser.add_argument(
        "--indexed-docs",
        type=str,
        default='indexed_docs.pickle',
        help="The file path to save the indexed output"
    )

    parser.add_argument(
        "--ssl-keyfile",
        type=str,
        default='',
        help="ssl key file"
    )

    parser.add_argument(
        "--ssl-certfile",
        type=str,
        default='',
        help="ssl cert file"
    )

    args = parser.parse_args()
    host = args.host
    port = args.port
    api_key = args.api_key
    if not api_key:
        if 'openai_api_key' in os.environ:
            api_key = os.environ['openai_api_key']
        else:
            raise ValueError('Please provide the openai api key')
    openai.api_key = api_key

    with open(args.indexed_docs, 'rb') as f:
        embeddings = pickle.load(f)

    uvicorn.run(app, host=host, port=port, ssl_keyfile=args.ssl_keyfile, ssl_certfile=args.ssl_certfile)

if __name__ == "__main__":
    main()
