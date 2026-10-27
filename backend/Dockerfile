FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# Unit 355 uses the psycopg v3 API. Keep the deployment image aligned with
# requirements-optional.txt without installing unrelated optional ML clients.
RUN pip install --no-cache-dir "psycopg[binary]>=3.2,<4"
COPY backend/app /app/app
COPY contracts/upstream/GMAIS-v0.2 /app/contracts/upstream/GMAIS-v0.2
ENV GEOAI_DATA_ROOT=/data
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
