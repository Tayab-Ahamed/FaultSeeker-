FROM python:3.11.9-slim-bookworm

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHON_DOTENV_DISABLED=true

COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --requirement requirements.lock
COPY . .

CMD ["python", "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"]
