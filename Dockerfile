FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app

RUN mkdir -p /app/policies /app/vector_store /app/audits /app/manual_review_cases

ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_PORT=8501

ENV HF_HOME=/app/.hf_cache
RUN mkdir -p /app/.hf_cache

EXPOSE 8501

#Initialize DB if needed, then start Streamlit
CMD ["bash", "-lc", "python bootstrap_db.py || true && streamlit run app.py --server.address=0.0.0.0 --server.port=8501"]
