FROM python:3.12-slim

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app

EXPOSE 8000 8501

CMD ["bash", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 & streamlit run ui.py --server.address 0.0.0.0"]

