FROM python:3.13-alpine

# Install build tools and dependencies
RUN apk add --no-cache build-base

WORKDIR /app

COPY requirements.txt .

# Install dependencies, including ruff and pytest
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run linting (fails on issues)
RUN ruff check .

# Run tests (fails on test failures)
RUN pytest

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
