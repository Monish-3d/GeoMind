import os , re
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from pinecone import Pinecone as PineconeClient, ServerlessSpec
from langchain_community.vectorstores import Pinecone as PineconeVectorStore
from langchain_community.embeddings import HuggingFaceEmbeddings
from dotenv import load_dotenv

load_dotenv()

def process_pdfs(folder , src_name):
    splitter = RecursiveCharacterTextSplitter(chunk_size = 1500 , chunk_overlap = 200)

    for file in os.listdir(folder):
        if not file.endswith(".pdf"): continue
        path = os.path.join(folder ,file)
        loader = PyPDFLoader(path)
        docs = loader.load()
        chunks = splitter.split_documents(docs)
        #chunks = splitter.create_documents([docs])

        for i , c in enumerate(chunks):
            match = re.search(r'(\d{4})', file)
            year = int(match.group(1)) if match else 'unknown' # changed year to int for now - not uploaded in pinecone

            c.metadata = {
                'source': src_name ,
                'filename' : file , 
                'year':year,
                'chunk_id': i
            }
    
        print("adding chunks to pinecone")
        vector_store.add_documents(chunks)
        print(f"Added {len(chunks)} chunks from {file} to Pinecone.")
        

#--------------------------------embedding model---------------------------------------
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

# embeddings = GoogleGenerativeAIEmbeddings(
#     model="models/gemini-embedding-001", # use -> 004??
#     google_api_key=api_key
# )

#------------------------------------creating vector database--------------------------
index_name = 'georag-index'
pinecone_api = os.getenv('PINECONE_API_KEY')

if not pinecone_api:
    raise ValueError("Pinecone api not found!")

pc = PineconeClient(api_key = pinecone_api)

existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
if index_name not in existing_indexes:
    print(f"creating new index: {index_name}")
    pc.create_index(
        name=index_name, 
        dimension= 768 ,
        metric = 'cosine',
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    print('Index created:' , index_name)
else:
    print("Index already exists:" , index_name)

index = pc.Index(index_name)
vector_store = PineconeVectorStore(index=index, embedding=embeddings , text_key='text')

#----------------------------uploading chunks-------------------------------------------

stats = index.describe_index_stats()
if stats.total_vector_count == 0:
    print("Uploading chunks.........")

    process_pdfs(os.path.join('data', 'raw_pdfs', 'imd_reports') , 'IMD')
    process_pdfs(os.path.join('data', 'raw_pdfs', 'MoEFCC_reports') , 'MoEFCC')

    print("all chunks uploaded")
else:
    print("index already has chunks")
    
stats = index.describe_index_stats()
print(f"Total vectors in index: {stats['total_vector_count']}")

