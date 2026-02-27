# Optimized Dockerfile for Python project
# Stage 1: Build dependencies
FROM python:3.11-alpine AS builder
# Install necessary build tools
RUN apk add --no-cache gcc musl-dev libffi-dev
WORKDIR /app
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --user --no-cache-dir -r requirements.txt; fi

# Stage 2: Minimal Runtime
FROM python:3.11-alpine
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY . .
# Replace 'main.py' with your entrypoint module if different
CMD ["python", "src/main.py"]
