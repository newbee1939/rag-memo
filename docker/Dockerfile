FROM python:3.10-bullseye

RUN apt-get update && apt-get -y install pipenv

WORKDIR /app

COPY . . 

RUN pipenv install --system
