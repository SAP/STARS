FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY . .

EXPOSE 8080
CMD [ "python", "main.py" ]
