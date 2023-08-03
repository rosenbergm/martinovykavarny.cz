FROM python:3.10-buster

EXPOSE 80

WORKDIR /app

RUN apt-get update
RUN apt-get install -y firefox-esr

RUN pip install --upgrade pip
RUN pip install poetry

COPY . /app

RUN poetry install --no-root

VOLUME [ "/data" ]
CMD [ "poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--proxy-headers" ]