# GeoMind  
Environmental Question-Answering with Spatial and Text Intelligence for India

GeoMind is an interactive environmental intelligence system that combines geospatial analysis with retrieval-augmented generation (RAG).  
Users can ask natural-language questions such as:

“How has forest cover near Chennai changed between 2010 and 2020?”

GeoMind processes the question by integrating:

- Geospatial context from multiple environmental layers  
- Evidence from government reports (MoEFCC, IMD)  
- Vector-based text retrieval  
- LLM reasoning (Gemini 2.5)  
- Interactive spatial visualization  

## Features

### Spatial Retrieval
- Reverse-geocodes user-specified locations  
- Identifies nearby features within roughly 40 km  
- Supports multiple spatial layers:  
  - Forest cover  
  - Aquifers  
  - Reservoirs  
  - Water structures  
  - Inter-basin transfer links  
- Computes accurate distance-to-feature metrics  

### Textual Retrieval (RAG)
- Retrieves relevant chunks from MoEFCC and IMD reports  
- Metadata-aware filtering (year, source, document)  
- Detects year ranges from user queries  
- Formats and cites textual evidence  

### Fusion Engine
- Merges spatial and textual evidence  
- Provides structured, grounded responses  
- Avoids hallucinated numbers by limiting to retrieved data  

### Interactive Mapping
- Folium-based interactive map rendered inside Streamlit  
- Color-coded layers  
- Supports polygons, lines, and points  
- Built-in legend overlay  

## Project Structure
```bash
GeoMind/
│
├── src/
│ ├── app.py # Streamlit frontend
│ ├── fusion_engine.py # Text + spatial reasoning
│ ├── geo_retriever.py # Shapefile loading and spatial queries
│ ├── geo_map_utils.py # Map rendering utilities
│ ├── text_retriever.py # Vector search logic
│ └── ingest_pdfs.py # PDF ingestion and embedding
│
├── data/
│ └── spatial/ # Shapefiles (ignored by Git)
│
├── .gitignore
├── requirements.txt
└── README.md
```
## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/GeoMind.git
cd GeoMind
conda create -n geomind python=3.12
conda activate geomind
pip install -r requirements.txt
```

## Environment Variables
Create a .env file in the project root:

```bash
GOOGLE_API_KEY=your-gemini-key
PINECONE_API_KEY=your-pinecone-key
PINECONE_INDEX_NAME=georag-index
```

## Running the Application

```bash
streamlit run src/app.py
```
visit
```bash
http://localhost:8501

```
## Data Sources

Place shapefiles inside data/spatial/.

Currently supported datasets:

FSI forest cover
NAQUIM aquifer boundaries
Reservoir boundaries
Water structures
Inter-basin water transfer links
MoEFCC annual reports
IMD climate reports

## Future Improvements

select area on map to get its information
add Major aquifer polygons
Time-series forest-cover visualization
Watershed/district-based querying
Geocoding cache
Environmental entity extraction
Additional environmental datasets

## Author

Developed by Monish Singhal
IIIT Una · AI/ML, GenAI