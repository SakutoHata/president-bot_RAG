from flask import Flask, request, Response, render_template, stream_with_context
from faiss_rag import RAGHandler
from csv_db_rag import search_Index 
from check_file import check_file_exists
from langchain.vectorstores.faiss import FAISS
from langchain_openai import AzureOpenAIEmbeddings
from openai import AzureOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize environment variables
FILE_PATH = os.environ["FILE_PATH"]
AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
LLM_MODELS = os.environ["LLM_MODELS"]
EM_MODELS = os.environ["EM_MODELS"]
MODE = os.environ["MODE"]

# Initialize models and vector store
embedding = AzureOpenAIEmbeddings(
    openai_api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    openai_api_type="azure",
    openai_api_key=AZURE_OPENAI_API_KEY,
    model=EM_MODELS,
)


vector_store = FAISS.load_local(f"{FILE_PATH}/db/faiss", embeddings=embedding, allow_dangerous_deserialization=True)
client = AzureOpenAI(api_key=AZURE_OPENAI_API_KEY, api_version="2024-08-01-preview", azure_endpoint=AZURE_OPENAI_ENDPOINT)

# Load prompts
## botのキャラクター性に関するもの
# 使用例
character_prompt_file_path = 'prompts/character_prompts.txt'
if check_file_exists(character_prompt_file_path):
    print("character_prompts ファイルが存在します")
    with open(f'{FILE_PATH}/prompts/character_prompts.txt', 'r', encoding='utf-8') as f:
        character_prompt = f.read()
else:
    print("character_prompts ファイルが存在しません")
    with open(f'{FILE_PATH}/prompts/character_prompts_Sample.txt', 'r', encoding='utf-8') as f:
        character_prompt = f.read()

## systemの設定
sys_prompt_file_path = 'prompts/system_prompts.txt'
if check_file_exists(sys_prompt_file_path):
    print("system_prompts ファイルが存在します")
    with open(f'{FILE_PATH}/prompts/system_prompts.txt', 'r', encoding='utf-8') as f:
        system_prompt = f.read()
else:
    print("system_prompts ファイルが存在しません")
    with open(f'{FILE_PATH}/prompts/system_prompts_Sample.txt', 'r', encoding='utf-8') as f:
        system_prompt = f.read()

# Initialize RAGHandler
rag_handler = RAGHandler(vector_store, client, character_prompt, system_prompt)

# Flask app setup
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    if MODE == "csv_index":
        contents = rag_handler.fetch_relevant_docs(user_message)
    else:
        contents = search_Index(user_message)
    updated_system_prompt = rag_handler.update_system_prompt(contents)

    def generate():
        yield from rag_handler.generate_stream(user_message, updated_system_prompt)

    return Response(stream_with_context(generate()), content_type='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)