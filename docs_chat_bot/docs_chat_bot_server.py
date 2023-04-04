import os
import time
import pickle
import argparse
import numpy as np
import openai
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pydantic import BaseModel

EMBEDDING_MODEL = "text-embedding-ada-002"

def get_embedding(text: str, model: str=EMBEDDING_MODEL) -> list[float]:
    result = openai.Embedding.create(
      model=model,
      input=text
    )
    return result["data"][0]["embedding"]


def vector_similarity(x: list[float], y: list[float]) -> float:
    """
    Returns the similarity between two vectors.
    
    Because OpenAI Embeddings are normalized to length 1, the cosine similarity is the same as the dot product.
    """
    return np.dot(np.array(x), np.array(y))

embeddings = None

def query(question):
    global embeddings
    print('+++++++question:', question)
    query_embedding = get_embedding(question)
    # print(query_embedding)
    document_similarities = sorted([
        (vector_similarity(query_embedding, doc_embedding), key) for key, doc_embedding in embeddings.items()
    ], reverse=True)

    context = []
    for similarity, document in document_similarities[:3]:
        context.append(document)
        print(similarity, document[:20])
    context = '\n'.join(context)
    # base on the following context and question, provide a conversational answer based on the context provided.:
    guide = """
I want you to act as an AI assistant, adept at analyzing provided text and answering questions based on the given context. When presented with extracted parts of a long document and a question, offer a conversational answer that is accurate and helpful. If the answer cannot be found within the provided context, simply respond with "Hmm, I'm not sure," without adding any speculative or extraneous information. Focus on delivering precise and reliable assistance based on the available information.
    """
    prompt = f'''
    {guide}
    ###
    {context}
    ###
    Question: {question}
    Answer:'''
        
    context_messages = []
    context_messages.append({"role": "system", "content":  guide})
    context_messages.append({"role": "user", "content": prompt})
    print(context_messages)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=context_messages
    )
    print('-'*100)
    ret = response['choices'][0]['message']['content']
    print(ret)
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
    print(data)
    message = data.message
    ret = query(message)
    response = {
        "status": "success",
        "received_message": ret
    }
    return response

def main():
    global embeddings
    import uvicorn
    parser = argparse.ArgumentParser(description="Chat-bot server")
    parser.add_argument(
        "--host",
        type=str,
        default='127.0.0.1',
        required=True,
        help="The host IP address for the chat-bot server, default to 127.0.0.1"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=7999,
        required=True,
        help="The port number for the chat-bot server, default to 7999"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default='',
        required=True,
        help="The openai api key or use the environment variable 'openai_api_key'"
    )
    
    parser.add_argument(
        "--indexed-docs",
        type=str,
        default='indexed_docs.pickle',
        required=True,
        help="The file path to save the indexed output"
    )

    args = parser.parse_args()
    host = args.host
    port = args.port
    api_key = args.api_key
    if not api_key:
        if 'openai_api_key' in os.environ:
            api_key = os.environ['openai_api_key']
        raise ValueError('Please provide the openai api key')
    openai.api_key = api_key

    with open(args.indexed_docs, 'rb') as f:
        embeddings = pickle.load(f)

    uvicorn.run(app, host=host, port=port)
if __name__ == "__main__":
    main()
