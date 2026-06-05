
async def search_var_for_v1(search_query, var_index_name, studies_index_name, search):
    elastic_results, total_count, aggregations = await search.search_elements(
        var_index_name,
        **search_query.model_dump()
    )

    results = []
    var2program = {}

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

                programs = studies["_source"]["programs"]
                for program in programs:

                    if program not in var2program:
                        var2program[program] = {}
                        var2program[program]["elements"] = []

                    var2program[program]["c_id"] =  studies["_source"]["id"]
                    var2program[program]["c_name"] = studies["_source"]["name"]
                    var2program[program]["c_link"] = studies["_source"]["action"]
                    var2program[program]["elements"].append(item)

    results.append(var2program)
    return results


async def search_concepts_for_v1(search_query, search):
    items, total_items, concept_types  = await search.search_concepts(**search_query.model_dump(exclude={"index"}))
    for item in items["hits"]["hits"]:
        del item["_source"]["tags"]
        del item["_source"]["programs"]
        del item["_source"]["parents"]
        del item["_source"]["element_type"]
        item["_source"]["type"] = item["_source"]["concept_type"]
        del item["_source"]["concept_type"]
        item["_source"]["concept_action"] = item["_source"]["action"]
        del item["_source"]["action"]

    all_items = dict(items.body.items())
    all_items["total_items"] = total_items
    all_items["concept_types"] = concept_types
    return  all_items
