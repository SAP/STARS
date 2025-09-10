FROM astral/uv:python3.11-trixie

WORKDIR /app

# Install uv for fast dependency management
# RUN pip install uv

# Copy dependency files first for better Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev --no-cache

# Copy the rest of the application
COPY . .

EXPOSE 8080
CMD ["uv", "run", "main.py"]
