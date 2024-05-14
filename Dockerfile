# app/Dockerfile

FROM python:3.10:alpine

WORKDIR /app

ADD . /app


RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 80

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "80"]