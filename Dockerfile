FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    libgl1 \
    libglib2.0-0 \
    wget \
    gnupg \
    unzip \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# copy requirements and install
COPY requirements_web.txt /app/requirements_web.txt
RUN pip install --upgrade pip setuptools wheel && pip install -r requirements_web.txt

# copy project
COPY . /app

# create runtime dirs
RUN mkdir -p /app/logs /app/data /tmp/nord_keywords /tmp/nord_logs

ENV FLASK_ENV=production
ENV FLASK_DEBUG=0
ENV FLASK_APP=run_flask.py
ENV PYTHONPATH=/app

EXPOSE 5000

CMD ["python", "run_flask.py"]
