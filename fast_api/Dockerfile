FROM python:3.13-slim

WORKDIR /app

COPY fast_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fast_api/ .
COPY machine_learning/ ./machine_learning/

EXPOSE 8000

CMD ["uvicorn", "predict:app", "--host", "0.0.0.0", "--port", "8000"]