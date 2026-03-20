source .env
export $(cut -d= -f1 .env)
export RANDOM=`dd if=/dev/random bs=64 count=1 2>/dev/null | base64`
export ELASTIC_API_HOST=localhost
export REDIS_HOST=localhost
