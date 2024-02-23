FROM python:3.10-bullseye

RUN apt-get update && apt-get -y install pipenv

RUN pipenv install --system

COPY . /app

WORKDIR /app
