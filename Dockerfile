FROM python:3.15.2-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip check
COPY . .
CMD ["python3", "run.py"]

FROM runtime AS test
RUN pip install --no-cache-dir pytest==9.2.0
CMD ["python3", "-m", "pytest", "-q", "-p", "no:cacheprovider"]

FROM runtime AS production
