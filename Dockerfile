FROM python:3.11.9-slim-bullseye

WORKDIR /app

# Update and upgrade system packages, then install build tools
RUN apt-get update && apt-get upgrade -y && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/vector_store data/uploads data/temp logs

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "app:app"]