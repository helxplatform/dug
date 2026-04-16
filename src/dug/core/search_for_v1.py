
async def search_var_for_v1(search_query, var_index_name, studies_index_name, search):
    elastic_results, total_count, aggregations = await search.search_elements(
        var_index_name,
        **search_query.model_dump()
    )

    results = []
    var2study = {}

    for result in elastic_results:
        source = result["_source"]
        item = {}
        item["id"] = source["id"]
        item["name"] = source["name"]
        item["score"] = result["_score"]
        item["e_link"] = source["action"]
        item["description"] = source["description"]
        item["metadata"] = source["metadata"]

        for p in source["parents"]:

            eresults, total_count, aggregations = await search.search_elements(studies_index_name, element_ids=[p])

            for studies in eresults:

                study_id = studies["_source"]["id"]
                if study_id not in var2study:
                    var2study[study_id] = {}
                    var2study[study_id]["elements"] = []

                var2study[study_id]["c_id"] = study_id
                var2study[study_id]["c_name"] = studies["_source"]["name"]
                var2study[study_id]["c_link"] = studies["_source"]["action"]
                var2study[study_id]["elements"].append(item)

    results.append(var2study)
    return results
