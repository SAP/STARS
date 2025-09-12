FROM astral/uv:python3.11-trixie-slim AS builder

# Install build dependencies including Rust for packages that need it
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    pkg-config \
    libssl-dev \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && . ~/.cargo/env \
    && rm -rf /var/lib/apt/lists/*

# Add Rust to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

# Copy dependency files first for better Docker layer caching
COPY pyproject.toml uv.lock ./

# Set environment variables to use CPU-only versions and reduce download size
ENV UV_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cpu"
ENV TORCH_INDEX_URL="https://download.pytorch.org/whl/cpu"

# Install dependencies using uv with proper build environment
RUN . ~/.cargo/env && \
    uv sync --frozen --no-dev --no-cache && \
    # Clean up any temporary files to reduce layer size
    rm -rf /root/.cache/uv /tmp/* /var/tmp/* && \
    # Remove Rust toolchain after build to reduce image size
    rustup self uninstall -y

# ----------------------------------------

FROM python:3.11-slim-trixie AS runtime

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl3 \
    libffi8 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy the virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Copy the rest of the application
COPY . .

# Make sure we use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

EXPOSE 8080
CMD ["python", "main.py"]
