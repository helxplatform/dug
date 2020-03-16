# Build

bin/comp build dug

# Run

docker run --rm --name dug --net=host -e "ELASTIC_API_HOST=localhost" -e "ELASTIC_API_PORT=9200" -e COMMAND="crawl" "heliumdatastage/dug"
docker run --rm --name dug --net=host -e "ELASTIC_API_HOST=localhost" -e "ELASTIC_API_PORT=9200" -e COMMAND="index" "heliumdatastage/dug"
docker run --rm --name dug --net=host -e "ELASTIC_API_HOST=localhost" -e "ELASTIC_API_PORT=9200" -e COMMAND="query coug" "heliumdatastage/dug"

