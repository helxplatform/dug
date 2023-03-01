source .env
export $(cut -d= -f1 .env)
export ELASTIC_API_HOST=localhost
export REDIS_HOST=localhost