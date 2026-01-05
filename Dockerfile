FROM python:3.11-bookworm

WORKDIR /app

# Install dependencies including netcat
COPY requirements.txt .
RUN apt-get update && apt-get install -y default-libmysqlclient-dev gcc netcat-traditional \
    && pip install --upgrade pip && pip install -r requirements.txt \
    && apt-get clean

# Copy project
COPY . .

# Entrypoint setup
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
