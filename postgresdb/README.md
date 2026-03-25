# VibeFinder PostgreSQL Database

Standalone PostgreSQL container for VibeFinder.

## Quick Start

```bash
# Create the network first (if not exists)
docker network create vibefinder-network

# Start PostgreSQL
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## Configuration

Copy `.env.example` to `.env` and adjust values:

```bash
cp .env.example .env
```

## Connection

- **Host**: localhost (or `postgres` from other containers)
- **Port**: 5432
- **Database**: vibefinder
- **User**: vibefinder
- **Password**: vibefinder123

### Connection String

```
postgresql://vibefinder:vibefinder123@localhost:5432/vibefinder
```

## Backups

Backups are stored in the `./backups` directory.

### Create a backup

```bash
docker exec vibefinder-postgres pg_dump -U vibefinder vibefinder > ./backups/backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore from backup

```bash
docker exec -i vibefinder-postgres psql -U vibefinder vibefinder < ./backups/backup_file.sql
```

## Data Persistence

Data is stored in a Docker volume named `vibefinder-postgres-data`.

To completely reset the database:

```bash
docker-compose down -v
docker-compose up -d
```

## Useful Commands

```bash
# Connect to psql
docker exec -it vibefinder-postgres psql -U vibefinder -d vibefinder

# Check database size
docker exec vibefinder-postgres psql -U vibefinder -c "SELECT pg_size_pretty(pg_database_size('vibefinder'));"

# List tables
docker exec vibefinder-postgres psql -U vibefinder -d vibefinder -c "\dt"
```
