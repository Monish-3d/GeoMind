import os
from langchain_community.vectorstores import Pinecone as PineconeVectorStore
from pinecone import Pinecone as PineconeClient
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
load_dotenv()

index_name = 'georag-index'
pinecone_api = os.getenv('PINECONE_API_KEY')

pc = PineconeClient(api_key = pinecone_api)
index = pc.Index(index_name)
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

#-----------------------------initialize vector store-------------------------------------
vector_store = PineconeVectorStore(index=index, embedding=embeddings , text_key='text')
#-----------------------------------------------------------------------------------------

def retrieve_text(query , k = 5 , source = None , year_range = None):
    filter_dict = dict()

    if source:
        filter_dict['source'] = {'$eq' : source}
    #=================================temporary fix ==========================
    if year_range:
        # Convert numeric range to list of string years
        years = [str(y) for y in range(year_range[0], year_range[1] + 1)]
        filter_dict["year"] = {"$in": years}

    # if year_range:
    #     filter_dict['year'] = {'$gte' : year_range[0] , "$lte" : year_range[1]}
    #=================================================================================

    docs = vector_store.similarity_search(query , k = k , filter= filter_dict if filter_dict else None)
    #retriever = vector_store.as_retriever(search_type ='similarity' , search_kwargs= {'k':k})

    results = []

    for d in docs:
        results.append({
            'content' : d.page_content,
            'metadata' : d.metadata
        })
    
    return results

# Example usage (temporary test)
if __name__ == "__main__":
    results = retrieve_text("Forest conservation policies in India", k=3, source=None, year_range=(2015, 2020))
    for r in results:
        print(f"\n {r['metadata']}")
        print(r['content'][:500], "...")

