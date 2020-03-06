# Build

bin/comp build search

# Run

docker run -it --rm --name search --env ELASTIC_API_HOST=<your-host> --env ELASTIC_API_PORT=9200 heliumdatastage/search
