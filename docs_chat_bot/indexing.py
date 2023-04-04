import os
import time
import pickle
import argparse
import logging
import numpy as np
import openai
import pandas as pd

EMBEDDING_MODEL = "text-embedding-ada-002"

logger = logging.getLogger(__name__)

def get_embedding(text: str, model: str=EMBEDDING_MODEL) -> list[float]:
    result = openai.Embedding.create(
      model=model,
      input=text
    )
    return result["data"][0]["embedding"]

def indexing_document(dir, output):

    tunks = []

    for root, dirs, files in os.walk(dir):
        for file in files:
            if file.endswith('.codon'):
                with open(os.path.join(root, file), 'r') as f:
                    code = f.read()
                    tunks.append(code)
            elif file.endswith('.md'):
                with open(os.path.join(root, file), 'r') as f:
                    code = f.read()
                    pieces = code.split(' '*100+'\n')
                    for piece in pieces:
                        tunks.append(piece.strip())

    embeddings = {}
    progress = 0
    start = time.time()
    for tunk in tunks:
        progress += 1
        if time.time() - start > 1:
            start = time.time()
            print(f'progress: %.2f%%' % (progress / len(tunks) * 100), end='\r')
        embedding = get_embedding(tunk)
        embeddings[tunk] = embedding

    with open(output, 'wb') as f:
        pickle.dump(embeddings, f)
    print('progress: 100.00%')

def indexing_main():
    parser = argparse.ArgumentParser(description="Chat-bot indexer")
    
    parser.add_argument(
        "--dir",
        type=str,
        default=".",
        help="The directory containing the documents to be indexed"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="indexed_docs.pickle",
        help="The file path to save the indexed output"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default='',
        help="The file path to save the indexed output"
    )

    args = parser.parse_args()
    
    api_key = args.api_key
    if not api_key:
        if 'openai_api_key' in os.environ:
            api_key = os.environ['openai_api_key']
        else:
            raise ValueError('Please provide the openai api key with the `--api-key` option or set the environment variable "openai_api_key"')

    openai.api_key = api_key
    document_dir = args.dir
    indexed_file = args.output
    indexing_document(document_dir, indexed_file)

if __name__ == "__main__":
    indexing_main()
