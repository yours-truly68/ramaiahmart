#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# RamaiahMart Production Deployment & Rollback Script
# ==============================================================================
# Invoked on AWS EC2 by GitHub Actions CD pipeline.
# Deploys an exact immutable Docker image tag from GHCR, executes database
# migrations safely, verifies health with retry polling, and provides automatic
# rollback if the deployment healthcheck fails.
# ==============================================================================

TARGET_IMAGE="${1:-${API_IMAGE:-}}"

if [ -z "$TARGET_IMAGE" ]; then
    echo "ERROR: TARGET_IMAGE (or API_IMAGE environment variable) is required."
    echo "Usage: ./deploy_prod.sh <ghcr.io/owner/ramaiahmart-api:commit-sha>"
    exit 1
fi

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
CURRENT_IMAGE_FILE=".current_image"
PREVIOUS_IMAGE_FILE=".previous_image"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE does not exist in working directory."
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "ERROR: $COMPOSE_FILE does not exist in working directory."
    exit 1
fi

echo "========================================================"
echo "Starting deployment for: $TARGET_IMAGE"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "========================================================"

# 1. Pull the exact immutable image from GHCR
echo "--> Pulling container image from GHCR..."
docker pull "$TARGET_IMAGE"

# 2. Run Alembic database migrations using the target image
echo "--> Executing Alembic database migrations..."
if ! docker run --rm --env-file "$ENV_FILE" "$TARGET_IMAGE" alembic upgrade head; then
    echo "ERROR: Alembic migration failed! Aborting deployment before container update."
    exit 1
fi
echo "--> Migrations applied successfully."

# 3. Preserve the previous known-good image for deterministic rollback
if [ -f "$CURRENT_IMAGE_FILE" ]; then
    PREV_IMAGE=$(cat "$CURRENT_IMAGE_FILE")
    echo "$PREV_IMAGE" > "$PREVIOUS_IMAGE_FILE"
    echo "--> Recorded previous known-good image: $PREV_IMAGE"
fi

# 4. Deploy updated container using Docker Compose
echo "--> Starting/updating containers with $TARGET_IMAGE..."
API_IMAGE="$TARGET_IMAGE" docker compose -f "$COMPOSE_FILE" up -d --remove-orphans api nginx

# 5. Healthcheck with retry polling (10 attempts, 3s sleep = 30s max)
echo "--> Verifying service health at /api/v1/health..."
MAX_ATTEMPTS=10
ATTEMPT=1
HEALTHY=false

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    echo "    Healthcheck attempt $ATTEMPT/$MAX_ATTEMPTS..."
    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80/api/v1/health || true)
    
    if [ "$STATUS_CODE" = "200" ]; then
        HEALTHY=true
        break
    fi
    
    # Also check direct container port in case Nginx port 80 is not bound to localhost
    CONTAINER_CODE=$(docker compose -f "$COMPOSE_FILE" exec -T api python -c "import urllib.request; resp = urllib.request.urlopen('http://localhost:8000/api/v1/health'); print(resp.getcode())" 2>/dev/null || true)
    if [ "$CONTAINER_CODE" = "200" ]; then
        HEALTHY=true
        break
    fi

    sleep 3
    ATTEMPT=$((ATTEMPT + 1))
done

if [ "$HEALTHY" = true ]; then
    echo "========================================================"
    echo "SUCCESS: Healthcheck passed! Deployment verified."
    echo "Active image: $TARGET_IMAGE"
    echo "========================================================"
    echo "$TARGET_IMAGE" > "$CURRENT_IMAGE_FILE"
    exit 0
else
    echo "========================================================"
    echo "CRITICAL: Healthcheck failed after $MAX_ATTEMPTS attempts."
    echo "Initiating automatic rollback to previous known-good state..."
    echo "========================================================"

    if [ -f "$PREVIOUS_IMAGE_FILE" ]; then
        ROLLBACK_IMAGE=$(cat "$PREVIOUS_IMAGE_FILE")
        echo "--> Rolling back to: $ROLLBACK_IMAGE"
        API_IMAGE="$ROLLBACK_IMAGE" docker compose -f "$COMPOSE_FILE" up -d --remove-orphans api
        
        # Verify rollback health
        sleep 5
        ROLLBACK_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80/api/v1/health || true)
        if [ "$ROLLBACK_STATUS" = "200" ]; then
            echo "--> Rollback succeeded. Previous version $ROLLBACK_IMAGE is healthy."
            echo "$ROLLBACK_IMAGE" > "$CURRENT_IMAGE_FILE"
        else
            echo "CRITICAL: Rollback failed to restore healthy service. Manual operator triage required!"
        fi
    else
        echo "WARNING: No $PREVIOUS_IMAGE_FILE found. Cannot perform automatic rollback."
    fi

    exit 1
fi
