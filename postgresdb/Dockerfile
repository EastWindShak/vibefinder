# PostgreSQL Dockerfile with initialization scripts
FROM postgres:16-alpine

# Copy initialization scripts (if any)
COPY init/ /docker-entrypoint-initdb.d/

# Set default environment variables
ENV POSTGRES_USER=vibefinder
ENV POSTGRES_PASSWORD=vibefinder123
ENV POSTGRES_DB=vibefinder

# Expose PostgreSQL port
EXPOSE 5432

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD pg_isready -U $POSTGRES_USER -d $POSTGRES_DB || exit 1
