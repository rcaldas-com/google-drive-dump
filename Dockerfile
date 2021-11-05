FROM python:3-alpine
LABEL maintainer="RCaldas <docker@rcaldas.com>"

COPY requirements.txt /
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app.py  mail.py /
ENTRYPOINT /app.py

VOLUME ["/files", "/credendial.json"]

