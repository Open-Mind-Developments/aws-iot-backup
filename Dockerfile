FROM python:3.9-slim
WORKDIR /usr/src/app

COPY src/ ./
COPY Pipfile Pipfile.lock ./
RUN python -m pip install --upgrade pip
RUN pip install pipenv && pipenv install --deploy --system

CMD [ "python", "./export.py" ]
