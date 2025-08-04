# UV Package Manager Setup

This project uses [UV](https://github.com/astral-sh/uv) for Python package management, which is significantly faster than pip.

## Single Dockerfile Approach

We use a single, optimized Dockerfile that works for both production and development:

- **Fast package installation** with UV
- **Production-ready** with security best practices
- **Development-friendly** with volume mounting
- **Autoscaling compatible** with Docker Swarm

## Performance Benefits

UV provides significant performance improvements:

- **5-10x faster** package installation
- **Parallel dependency resolution**
- **Intelligent caching**
- **Lock file generation** for reproducible builds

## Usage

### Production
```bash
# Uses the optimized Dockerfile with UV
docker-compose up

# Or with Docker Swarm for autoscaling
docker swarm init
docker stack deploy -c docker-compose.swarm.yml sastaspace
```

### Development
```bash
# Same Dockerfile, but with volume mounting for hot reload
docker-compose up

# Or run locally with UV
cd backend
uv sync
uv run python manage.py runserver
```

## Key Features

### 1. Dependency Management
- `pyproject.toml` defines all dependencies
- `uv sync --no-dev` installs production dependencies
- `uv sync` installs all dependencies (including dev)

### 2. Virtual Environment
- UV automatically manages virtual environments
- No need to manually create/activate venv
- `uv run` executes commands in the virtual environment

### 3. Lock File
- `uv.lock` ensures reproducible builds
- Committed to version control
- Guarantees same dependency versions across environments

## Dockerfile Features

- **UV package manager** for fast installations
- **Non-root user** for security
- **Optimized layer caching** with pyproject.toml copied first
- **Production-ready** with proper environment variables
- **Development-friendly** with volume mounting support

## Performance Tips

1. **Use `uv sync --no-dev`** for production builds
2. **Leverage Docker layer caching** by copying `pyproject.toml` first
3. **Use `uv.lock`** for reproducible builds
4. **Set `UV_CACHE_DIR`** for persistent caching

## Comparison with pip

| Feature | pip | UV |
|---------|-----|-----|
| Installation Speed | ~1x | ~5-10x |
| Dependency Resolution | Sequential | Parallel |
| Lock File | requirements.txt | uv.lock |
| Virtual Environment | Manual | Automatic |
| Caching | Basic | Advanced |

## Troubleshooting

### Common Issues

1. **UV not found in container:**
   ```bash
   # Rebuild the image
   docker-compose build --no-cache
   ```

2. **Permission issues:**
   ```bash
   # The Dockerfile creates a non-root user
   # If you need root access, modify the Dockerfile
   ```

3. **Cache issues:**
   ```bash
   # Clear UV cache
   rm -rf /tmp/uv-cache
   ```

## Next Steps

1. **Test the setup:**
   ```bash
   docker-compose up --build
   ```

2. **For autoscaling:**
   ```bash
   docker swarm init
   docker stack deploy -c docker-compose.swarm.yml sastaspace
   ```

3. **Local development:**
   ```bash
   cd backend
   uv sync
   uv run python manage.py runserver
   ``` 