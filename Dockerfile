FROM python:3.11-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev libffi-dev
WORKDIR /app
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --user --no-cache-dir -r requirements.txt; fi

# Stage 2: Minimal Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY . .
ENV PYTHONPATH=/app/src
CMD ["python", "src/main.py"]
