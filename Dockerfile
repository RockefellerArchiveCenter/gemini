FROM python:3.10

ENV PYTHONUNBUFFERED 1

RUN apt-get update \
    && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code/

COPY requirements.txt /code/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . /code/

EXPOSE 8006

ENTRYPOINT ["/code/entrypoint.sh"]
