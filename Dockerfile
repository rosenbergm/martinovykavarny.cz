FROM python:3.10-alpine

EXPOSE 80

WORKDIR /app

RUN apk update
RUN apk add firefox 

RUN pip install --upgrade pip
RUN pip install poetry

COPY . /app

RUN poetry install --no-root

CMD [ "poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--proxy-headers" ]