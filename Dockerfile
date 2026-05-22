FROM python:3.11-slim-bullseye

WORKDIR /app

RUN python -m pip install --upgrade pip

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY bot ./bot

COPY main.py .

CMD ["python", "main.py"]