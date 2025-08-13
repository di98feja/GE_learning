FROM homeassistant/home-assistant:stable

# Install additional system dependencies (Alpine Linux - uses apk)
USER root

# Install system packages
RUN apk add --no-cache \
    build-base \
    python3-dev \
    libffi-dev \
    openssl-dev \
    jpeg-dev \
    zlib-dev \
    autoconf \
    openjpeg-dev \
    tiff-dev \
    libjpeg-turbo-dev \
    tzdata \
    curl \
    gcc \
    musl-dev \
    shadow

# Create ge_admin user with proper permissions
RUN adduser -D -s /bin/ash -u 1000 ge_admin && \
    addgroup ge_admin dialout && \
    addgroup ge_admin audio

# Create config directory and set permissions
RUN mkdir -p /config && \
    chown -R ge_admin:ge_admin /config

# Copy requirements file and install Python packages as root
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy custom components and set ownership
COPY custom_components/ /config/custom_components/
RUN chown -R ge_admin:ge_admin /config/custom_components/

# Switch to ge_admin user
USER ge_admin

# Set the working directory
WORKDIR /config

# Expose Home Assistant port
EXPOSE 8123

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8123/api/ || exit 1