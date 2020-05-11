# Build

bin/comp build dug

# Run

docker run --rm --name dug --net=host -e "ELASTIC_API_HOST=localhost" -e "ELASTIC_API_PORT=9200" -e COMMAND="crawl" "heliumdatastage/dug"
docker run --rm --name dug --net=host -e "ELASTIC_API_HOST=localhost" -e "ELASTIC_API_PORT=9200" -e COMMAND="index" "heliumdatastage/dug"
docker run --rm --name dug --net=host -e "ELASTIC_API_HOST=localhost" -e "ELASTIC_API_PORT=9200" -e COMMAND="query coug" "heliumdatastage/dug"

# Automated Builds

Automated DockerHub builds trigger two ways:

  * On commits to helxplatform/dug in GitHub, which emits a DockerHub build with the tag **latest**, and 
  * When a version tag of the form vn.n.n (e.g. v0.1.2) is pushed to GitHub, which emits a DockerHub build with the same tag.

DockerHub only creates builds with version numbers from tagged GitHub commits. If you push a GitHub commit with a tag it will create both the latest and vn.n.n versions.

When you create a tag, it has to be pushed to the remote and it uses slightly different syntax:
   ```
   git tag v0.1.2
   git push origin v0.1.2
   ```

You can also list tags with:
   ```
   git tag -l
   ```

And delete a tag locally:
   ``` 
   git tag -d v0.1.2
   ```

And remotely:
   ```
   git push origin :refs/tags/v0.1.2
   ```
