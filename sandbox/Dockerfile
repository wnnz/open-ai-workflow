FROM python:3.12-slim
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
WORKDIR /service
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN useradd --create-home --uid 10001 sandbox \
    && mkdir -p /workspace /data/files /data/sandbox-artifacts \
    && chown -R root:root /service /workspace /home/sandbox /data/files \
    && chown sandbox:sandbox /data/sandbox-artifacts \
    && chmod -R a-w /service /workspace /home/sandbox /data/files
USER sandbox
EXPOSE 8081
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8081"]
