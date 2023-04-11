FROM debian:bullseye-slim

WORKDIR /usr/src/app
COPY app2.py .
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip iputils-ping && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

CMD ["python3", "-u", "app2.py"]

