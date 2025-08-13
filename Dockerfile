FROM homeassistant/home-assistant:stable

# Install additional system dependencies
USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    autoconf \
    build-essential \
    libopenjp2-7 \
    libtiff5 \
    libturbojpeg0-dev \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Switch back to the homeassistant user
USER abc

# Copy requirements file for additional Python packages
COPY requirements.txt /tmp/requirements.txt

# Install additional Python packages
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy custom components
COPY custom_components/ /config/custom_components/

# Set the working directory
WORKDIR /config

# Expose Home Assistant port
EXPOSE 8123

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8123/api/ || exit 1