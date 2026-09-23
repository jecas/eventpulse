FROM python:3.12-slim
WORKDIR /app
COPY mock_external ./mock_external
RUN pip install --no-cache-dir "fastapi>=0.115,<1.0" "uvicorn[standard]>=0.34,<1.0"
CMD ["uvicorn", "mock_external.main:app", "--host", "0.0.0.0", "--port", "9000"]
