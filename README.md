## ITI122 Generative AI Assignment

This project is a prototype GenAI-powered loan risk assessment system that:
- Retrieves customer data from simulated systems
- Applies policy rules via Retrieval-Augmented Generation (RAG)
- Uses Gemini for reasoning and explanation
- Generates both internal decision notes and applicant-facing letters
- Supports human-in-the-loop manual review escalation

## Tech Stack
- Python 3.12
- Streamlit
- SQLite (simulated systems)
- FAISS + sentence-transformers (RAG)
- Gemini API
- Docker / Docker Compose



## Running locally
```bash
export GEMINI_API_KEY="YOUR_API_TOKEN"
python bootstrap_db.py
streamlit run app.py
```

## Docker:
```bash 
docker compose up --build
```

## Live Demo:
`iti122.jackhww.me` 
- Access to the Demo will be given on request. 
The URL is publicly available and this is to prevent overspending of Gemini Tokens which are on free tier right now.

## Notes
- Policy PDFs go in `policies/`
- GEMINI_API_KEY must be provided via an Environment Variable