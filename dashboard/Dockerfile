FROM python:3.11-slim

# ffmpeg for video rendering/clipping; fonts for burned-in captions
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg fonts-dejavu-core git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

# Copy the whole repo (dashboard/ needs the sibling agents/ package)
COPY . /srv

RUN pip install --no-cache-dir -r dashboard/requirements.txt

WORKDIR /srv/dashboard

# Persisted across deploys via a Coolify volume mounted at /srv/dashboard/data
ENV DASHBOARD_DB_PATH=/srv/dashboard/data/dashboard.db

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
