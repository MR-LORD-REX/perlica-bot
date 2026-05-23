FROM python:3.11-slim-bullseye

WORKDIR /app

RUN python -m pip install --upgrade pip

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY bot ./bot

COPY main.py .

EXPOSE 8000

CMD ["python", "main.py"]