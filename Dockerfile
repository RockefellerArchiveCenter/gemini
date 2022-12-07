FROM python:3.10

ENV PYTHONUNBUFFERED 1

RUN apt-get update \
    && apt-get install -y \
      postgresql \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code/gemini/

COPY requirements.txt /code/gemini/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . /code/gemini/

EXPOSE 8006

ENTRYPOINT ["/code/gemini/entrypoint.sh"]
