FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY examples ./examples

RUN pip install --no-cache-dir ".[example]"

USER app
EXPOSE 8000

CMD ["uvicorn", "examples.app:app", "--host", "0.0.0.0", "--port", "8000"]
