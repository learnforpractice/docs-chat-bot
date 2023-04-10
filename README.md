chat plugin for mkdocs

## Instalation
```bash
python3 -m pip install docs-chat-bot
```

## Usage

Add chat plugin to your mkdocs.yml file.

example:

```yaml
plugins:
    - chat
        docs_chat_endpoint: "http://localhost:7999/chat"
```

Before using the chatbot, there are three essential tasks to complete:

1. Indexing the documents
2. Running a document chatbot server

This guide will walk you through each step to ensure a seamless experience with the chatbot.

## Indexing the documents

To enable the chatbot to access and retrieve information from your documents, they must be indexed first. Indexing the documents will create a searchable data structure that allows the chatbot to quickly locate relevant information when responding to user queries.

The `indexing_docs` command is used to index a collection of documents using the OpenAI Embedding Interface. 

usage:

```bash
indexing_docs --dir [markdown document dir] --api-key [openai api key]
```

This command indexes the documents in the specified directory using the OpenAI Embedding Interface, with the following options:

1. `--dir`: Specifies the directory containing the markdown documents to be indexed.
2. `--api-key`: Sets the API key used to authenticate with the OpenAI API.

**Attention** 

Please be aware that this tool does not provide automatic document segmentation functionality. To ensure optimal usage with the ChatGPT API, it is crucial to follow the guidelines for document segmentation provided below.

Document Segmentation Guidelines
--------------------------------

1. Manual segmentation: If a Markdown file is too large, you must manually split it into smaller segments. Ensure that each segment has a gap of 100 spaces.

2. Segment length: Each document segment should not exceed 2,000 words. Exceeding this limit may result in segments that are too large to fit within the constraints of the ChatGPT API.

How to Segment Documents
------------------------

1. Open the large Markdown file in a text editor of your choice.

2. Identify a suitable point in the document to split it into smaller segments. This could be a natural break, such as a section or chapter boundary.

3. Separate the segments with 100 spaces, ensuring that each segment does not exceed the 3,000-word limit.


## Running a document chatbot server

Once your documents are indexed, you will need to set up and run a document chatbot server. The server is responsible for processing user input, searching the indexed documents, and returning appropriate responses based on the information found within the documents.

`docs_chat_bot_server --indexed-docs [indexed document] --api-key [openai API key]`

This command launches the chatbot server with the following options:

1. `--indexed-docs`: Specifies the file containing indexed documents to be used by the chatbot server for retrieving information.
2. `--api-key`: Sets the API key used to authenticate with external openai chatgpt services.
