FROM python:3.12-slim

# System deps (some PDF/text libs benefit from these)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app code
COPY . /app

# Create runtime dirs (will be overwritten by volumes if you mount them)
RUN mkdir -p /app/policies /app/vector_store /app/audits /app/manual_review_cases

# Streamlit config to listen on all interfaces
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

EXPOSE 8501

# Bootstrap DB at container start if missing, then run Streamlit
CMD ["bash", "-lc", "python bootstrap_db.py || true && streamlit run app.py --server.port=8501 --server.address=0.0.0.0"]
