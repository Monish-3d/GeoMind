import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

from text_retriever import retrieve_text
from geo_retriever import get_spatial_context, summarize_spatial_context

from typing import List , Tuple , Optional , Dict

load_dotenv()

#--------------------------------------------------------------------------------------

llm = ChatGoogleGenerativeAI(model='gemini-2.5-pro')

def format_text_content(docs : List[Dict] , max_chars:9000)-> str:
    ''' format chunks with metadata '''
    parts = []
    total = 0

    for d in docs:
        meta = d.get('metadata' , {})

        tag = (
            f"[src:{meta.get('source','?')} | file:{meta.get('filename','?')} | "
            f"year:{meta.get('year','?')} | chunk:{meta.get('chunk_id','?')}]"
        )
        text = d.get('content', '').strip().replace('\n' , ' ')
        
        snippet = f'{tag}\n{text}\n'

        if total + len(snippet) > max_chars:
            break

        parts.append(snippet)
        total += len(snippet)

    return "\n".join(parts) if parts else "No textual evidence retrieved."


def unique_source(docs : List[Dict]) -> str:
    '''collect source '''
    seen = set()
    out = []

    for d in docs:
        meta = d.get('metadata', {})
        tup = (meta.get('source') , meta.get('filename') , meta.get('year'))

        if tup not in seen:
            seen.add(tup)
            out.append(f"{meta.get('source')} · {meta.get('filename')} · {meta.get('year')}")
    
    return out

def build_prompt(user_query : str , text_block: str , spatial_block: str , year_range: str) -> str:
    '''combine text and spatial for final prompt'''

    template = PromptTemplate(
        template="""You are GeoMind — an environmental intelligence system for India.

        Your job is to answer the user's query using BOTH:
        1. **Textual evidence** from MoEFCC/IMD reports  
        2. **Geospatial evidence** from aquifer maps, forest cover, reservoirs, inter-basin links and structures 
        3. The extracted year range mentioned in the query

        USER QUERY:
        {user_query}

        DETECTED YEAR RANGE:
        {year_range}

        -----------------------------------------------------------
        TEXTUAL EVIDENCE (chunk-tagged):
        {text_block}

        -----------------------------------------------------------
        SPATIAL CONTEXT:
        {spatial_block}

        -----------------------------------------------------------
        INSTRUCTIONS:
        - Combine textual + spatial reasoning.
        - Be factual and cite textual chunks like (src:MoEFCC · 2019).
        - If spatial context contradicts text, explain why.
        - If time range is mentioned (e.g., 2010-2020), analyze accordingly.
        - Avoid hallucinating numbers, use only available evidence.
        - If insufficient evidence exists, explicitly say so.

        Now produce a concise, well-structured answer integrating BOTH signals.
        """,
        input_variables=['user_query' , 'text_block' , 'spatial_block' , 'year_range']
        )
    
    return template.format(user_query = user_query, text_block = text_block, spatial_block = spatial_block ,year_range = year_range)

def get_year_range(query : str) -> Optional[Tuple[int,int]]:
    year_range_llm = ChatGoogleGenerativeAI(model= 'gemini-2.5-flash-lite',temperature=0.0)

    template = PromptTemplate(
        template= '''Extract the YEAR RANGE from the question.
        Return ONLY two integers: start_year end_year.
        If only one year exists (e.g., "since 2015"), return: 2015 CURRENT_YEAR.
        If no range, return NONE.

        Example:
        "forest cover from 2010 to 2020" -> 2010 2020
        "changes since 2015" -> 2015 2024
        "impact on rainfall" -> NONE

        Query: {query} 
        Year Range:
        ''',
        input_variables=['query']
    )
    prompt = template.format(query = query)
    years = year_range_llm.invoke(prompt)
    res = years.content.strip().replace("\n", " ")

    if res.upper() == "NONE":
        return None
    
    parts = res.split()
    if len(parts) != 2:
        return None
    
    try:
        start, end = map(int, parts)
        return (start, end)
    except:
        return None

def get_location(query : str) -> str:
    location_llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash-lite',temperature=0.0)

    template = PromptTemplate(
        template='''Extract ONLY the geographic place name from the following question.
        Return ONLY the name. No extra words.

        Examples:
        "How has forest cover near Chennai changed from 2010 to 2020?" -> Chennai
        "Aquifer depth in Kota district" -> Kota
        "Rainfall trends in North East India" -> North East India
        "Show changes around Pune city" -> Pune

        Query: {query} 
        Location:
        ''',
        input_variables=['query']
    )
    prompt = template.format(query = query)
    location = location_llm.invoke(prompt)

    return location.content.strip()


def fuse_query(user_query: str , k : int = 12 , source : Optional[str]  = None, year_range : Optional[Tuple[int , int]] = None) -> Dict:
    ''' get llm response '''

    if year_range is None:
        auto_year_range = get_year_range(user_query)
    else:
        auto_year_range = year_range

    #-------------------------text retrieval------------------------------------
    text_docs = retrieve_text(query= user_query , k= k , source= source , year_range= auto_year_range)

    text_block = format_text_content(text_docs , 9000)

    #-------------------------spatial retrieval---------------------------------

    location = get_location(user_query)

    spatial_raw = get_spatial_context(location)

    # import json
    # print("\n====== DEBUG SPATIAL RAW ======\n")
    # print(json.dumps(spatial_raw, indent=2, default=str)[:3000])
    # print("\n===============================\n")

    spatial_summary = summarize_spatial_context(spatial_raw)

    #----------------------get final llm prompt-----------------------------------
    
    prompt = build_prompt(user_query= user_query , text_block=text_block , spatial_block= spatial_summary , year_range=auto_year_range)

    #-----------------------invoking the llm--------------------------------------
    
    response = llm.invoke(prompt)

    answer = response.content

    sources = unique_source(text_docs)

    return {
        'answer' : answer,
        'spatial_summary' : spatial_summary,
        'spatial_raw' : spatial_raw,
        'text_chunks' : text_docs,
        'sources' : sources,
        'year_range' : auto_year_range
    }

#-------------------------test-------------------------------------

if __name__ == "__main__":
    q  = 'how has the forest cover near chennai changed'

    result = fuse_query(q , year_range=(2015 , 2020))

    print("\n============= ANSWER ============\n" , result['answer'])
    print("\n============= SOURCES ===========\n")

    for s in result['sources']:
        print(' -' , s)
        
    print("\n======== spatial summary ========\n" , result['spatial_summary'])



