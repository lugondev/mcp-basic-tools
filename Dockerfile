FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY main.py ./
COPY tools ./tools

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[search]"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
