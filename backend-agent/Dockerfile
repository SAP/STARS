FROM astral/uv:python3.11-trixie-slim AS builder

# Install build dependencies with minimal footprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y

# Install Rust with minimal profile and immediate cleanup
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal \
    && . ~/.cargo/env \
    && rustup component add rustfmt

# Add Rust to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

# Copy dependency files first for better Docker layer caching
COPY pyproject.toml uv.lock ./

# Set environment variables to use CPU-only versions and reduce download size
ENV UV_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cpu"
ENV TORCH_INDEX_URL="https://download.pytorch.org/whl/cpu"

# Install dependencies with aggressive progressive cleanup
RUN . ~/.cargo/env && \
    # Install dependencies with bytecode compilation for better performance
    uv sync --frozen --no-dev --no-cache --compile-bytecode && \
    # Immediate cleanup of build artifacts during installation
    find /app/.venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -name "*.pyc" -delete 2>/dev/null || true && \
    find /app/.venv -name "*.pyo" -delete 2>/dev/null || true && \
    # Remove test files and documentation from packages (keeping runtime libs)
    find /app/.venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type d -name "test" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type d -name "docs" -exec rm -rf {} + 2>/dev/null || true && \
    # Strip debug symbols from shared libraries to reduce size
    find /app/.venv -name "*.so" -exec strip {} + 2>/dev/null || true && \
    # Aggressive cache and temporary file cleanup
    rm -rf /root/.cache/uv \
           /root/.cache/pip \
           /root/.cache/* \
           /tmp/* \
           /var/tmp/* \
           /root/.cargo/registry \
           /root/.cargo/git \
           /app/.venv/share \
           && \
    # Remove Rust toolchain completely after build
    rustup self uninstall -y && \
    # Final build tools cleanup to free space
    apt-get autoremove -y build-essential git curl pkg-config && \
    apt-get autoclean

# ----------------------------------------

FROM python:3.11-slim-trixie AS runtime

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 \
    libffi8 \
    # Add required libraries for ML packages
    libgomp1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get autoclean

WORKDIR /app

# Copy the virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Copy the application
COPY . .

# Make sure we use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

EXPOSE 8080
CMD ["python", "main.py"]
