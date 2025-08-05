#!/bin/bash
# Local deployment script for SastaSpace

# Start Django backend
cd ../backend
source venv/bin/activate
gunicorn sastaspace_project.wsgi:application --bind 0.0.0.0:8000 &

# Start React frontend
cd ../frontend
npm run build
npx serve -s dist -l 3000 &

# Cloudflare Tunnel setup instructions:
# 1. cloudflared tunnel login
# 2. cloudflared tunnel create sastaspace-tunnel
# 3. cloudflared tunnel route dns sastaspace-tunnel sastaspace.com
# 4. Create config.yml:
# tunnel: <Tunnel-UUID>
# credentials-file: /path/to/your/.cloudflared/<Tunnel-UUID>.json
# ingress:
#   - hostname: sastaspace.com
#     service: http://localhost:3000
#   - hostname: api.sastaspace.com
#     service: http://localhost:8000
#   - service: http_status:404
# 5. cloudflared tunnel run sastaspace-tunnel
