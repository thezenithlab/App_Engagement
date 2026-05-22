FROM python:3.12-slim

WORKDIR /app

# Install lightweight dependencies
RUN pip install --no-cache-dir fastapi uvicorn

# Copy the dashboard script and pre-compiled database
COPY dashboard_hicss.py /app/dashboard_hicss.py
COPY exports/HICSS60_classified_apps.db /app/exports/HICSS60_classified_apps.db

# Expose the default FastAPI/Uvicorn port
EXPOSE 8500

# Set environment variables for clean logs
ENV PYTHONUNBUFFERED=1

# Start the dashboard server
CMD ["python", "dashboard_hicss.py"]
