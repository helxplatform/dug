import json
from dug.utils import biolink_snake_case


class MissingNodeReferenceError(BaseException):
    pass


class MissingEdgeReferenceError(BaseException):
    pass


class QueryKG:
    def __init__(self, kg_json):
        self.kg = kg_json["message"]
        self.answers = self.kg.get("results", [])
        self.question = self.kg.get("query_graph", {})
        self.nodes = self.kg.get("knowledge_graph", {}).get("nodes") # {node["id"]: node for node in kg_json.get('knowledge_graph', {}).get('nodes', [])}
        self.edges = self.kg.get("knowledge_graph", {}).get("edges") # {edge["id"]: edge for edge in kg_json.get('knowledge_graph', {}).get('edges', [])}

    def get_answer_subgraph(self, answer, include_node_keys=[], include_edge_keys=[]):

        # Get answer nodes
        answer_nodes = {}
        for binding_id, binding_nodes in answer["node_bindings"].items():
            # Add node info for each node included in answer graph
            for answer_node in binding_nodes:
                # Throw error if node doesn't actually exist in 'nodes' section of knowledge graph
                if answer_node["id"] not in self.nodes:
                    err_msg = f"Unable to assemble subraph for answer:\n{json.dumps(answer, indent=2)}\n" \
                              f"Parent graph doesn't contain node info for: {answer_node}"
                    raise MissingNodeReferenceError(err_msg)

                # Add only node info that you actually want
                answer_nodes[answer_node["id"]] = self.get_node(answer_node["id"], include_node_keys)

        # Get answer edges
        answer_edges = {}
        for binding_id, binding_edges in answer["edge_bindings"].items():
            # Add edge info for each edge included in answer graph
            for answer_edge in binding_edges:
                # Throw error if edge doesn't actually exist in 'edges' section of knowledge graph
                if answer_edge["id"] not in self.edges:
                    err_msg = f"Unable to assemble subraph for answer:\n{json.dumps(answer, indent=2)}\n" \
                        f"Parent graph doesn't contain edge info for: {answer_edge}"
                    raise MissingEdgeReferenceError(err_msg)

                # Add only information from edge that you actually want
                answer_edges[answer_edge["id"]] = self.get_edge(answer_edge["id"], include_edge_keys)

        kg = {"message":{
                "knowledge_graph": {
                    "nodes": answer_nodes,
                    "edges": answer_edges
                        },
                "results": [answer],
                "query_graph": self.question
                }
              }

        return QueryKG(kg)

    def _parse_attributes(self, kg_component):
        """
        Extracts attributes to normal dict from Trapi 1.0 KG nodes / edges
        Trapi 1.0 has {"id": "xxx", "name": "xxx", "attributes" : {"name": "publication", "value": "xxx",...}}
        :param kg_component: Dict representing a node or an edge
        :return:
        """
        return {attr["name"]: attr["value"] for attr in kg_component.get("attributes", {})}

    def get_node(self, node_id, include_node_keys=[]):
        # Return node with optionally subsetted information
        # Trapi 1.0 has {"id": "xxx", "name": "xxx", "attributes" : [{"name": "publication", "value": "xxx"...}, {},...]}
        node = self._parse_attributes(self.nodes[node_id])
        node.update({k: v for k, v in self.nodes[node_id].items() if k != "attributes"})

        node["id"] = node_id
        node["name"] = self.nodes[node_id].get("name", "")
        # Optionally subset to get only certain information columns
        if include_node_keys:
            node = {key: node.get(key) for key in include_node_keys}
        return node

    def get_edge(self, edge_id, include_edge_keys=[]):
        # Return edge with optionally subsetted information
        edge = self._parse_attributes(self.edges[edge_id])
        edge.update({k: v for k, v in self.edges[edge_id].items() if k != "attributes"})

        edge["id"] = edge_id
        edge["publications"] = edge.get("publications", [])
        if isinstance(edge["publications"], str):
            edge["publications"] = [edge["publications"]]
        # Optionally subset to include only certain info
        if include_edge_keys:
            edge = {key: edge.get(key) for key in include_edge_keys}
        return edge

    def get_nodes(self):
        nodes_dict = self.kg.get("knowledge_graph", {}).get("nodes", {})
        return [self.get_node(curie) for curie in nodes_dict]

    def get_edges(self):
        edges_dict = self.kg.get("knowledge_graph", {}).get("edges", {})
        return [self.get_edge(kg_id) for kg_id in edges_dict]

    def get_node_names(self, include_curie=True):
        node_names = []
        curie_ids = self.get_curie_ids()
        for node in self.get_nodes():
            if include_curie or node['id'] not in curie_ids:
                node_names.append(node['name'])
        return node_names

    def get_node_synonyms(self, include_curie=True):
        # @TODO call name-resolver 
        node_synonyms = []
        curie_ids = self.get_curie_ids()
        for node in self.get_nodes():
            if include_curie or node['id'] not in curie_ids:
                syn = node.get('synonyms') 
                if isinstance(syn,list):
                    node_synonyms +=  syn 
        return node_synonyms

    def get_curie_ids(self):
        question_nodes_dict = self.question.get('nodes', {})
        return [question_nodes_dict[node]['id'] for node in question_nodes_dict if 'id' in question_nodes_dict[node]]

    def get_kg(self):
        # Parse out the KG in whatever form we want
        # TODO: Make this parse out old-style json so ui doesn't break
        old_kg_model = {
            "knowledge_map": [],
            "knowledge_graph": {
                "nodes": [],
                "edges": [],
            },
            "question_graph": {
                "nodes": [],
                "edges": []
            }
        }
        query_graph = self.kg.get("query_graph")
        for q_id in query_graph["nodes"]:
            node_details = query_graph["nodes"][q_id]
            node_curie = node_details.get("id", "")
            category = node_details.get("category", [])
            if type(category) == list:
                node_type = [self._snake_case(x.replace('biolink.', '')) for x in category]
            else:
                node_type = [self._snake_case(category.replace('biolink.', ''))]
            old_node = {"id": q_id, "type": node_type}
            if node_curie:
                old_node.update({"curie": node_curie})
            old_kg_model["question_graph"]["nodes"].append(old_node)

        for q_id in query_graph["edges"]:
            edge_details = query_graph["edges"][q_id]
            old_edge = {"id": q_id, "source_id": edge_details["subject"], "target_id": edge_details["object"]}
            edge_type = edge_details.get("predicate")
            if edge_type:
                old_edge.update({"type": edge_type})
            old_kg_model["question_graph"]["edges"].append(old_edge)

        results = self.kg.get("results")
        for bindings in results:
            old_binding = {}
            for binding_type in bindings:
                for q_id in bindings[binding_type]:
                    kg_ids = [x["id"] for x in bindings[binding_type][q_id]]
                    old_binding[binding_type] = old_binding.get(binding_type, {})
                    old_binding[binding_type][q_id] = old_binding[binding_type].get(q_id,[])
                    old_binding[binding_type][q_id] = kg_ids
            old_kg_model["knowledge_map"].append(old_binding)
        old_kg_model["knowledge_graph"]["nodes"] = self.get_nodes()
        for node in old_kg_model["knowledge_graph"]["nodes"]:
            # adds id for node name if no name is present
            node["name"] = node["name"] if node["name"] else node["id"]
        old_kg_model["knowledge_graph"]["edges"] = self.get_edges()
        for edge in old_kg_model["knowledge_graph"]["edges"]:
            # adds predicate as type for edges
            edge["type"] = edge["predicate"]
            # source_id and target_id should always be str
            edge["source_id"] = edge["subject"]
            edge["target_id"] = edge["object"]
        return old_kg_model

    def _snake_case(self, arg: str):
        return biolink_snake_case(arg)


class InvalidQueryError(BaseException):
    pass


class QueryFactory:

    # Class member list of valid data types that can be included in query
    data_types = ["publication", "phenotypic_feature", "gene", "disease", "chemical_substance",
                  "drug_exposure", "biological_process", "anatomical_entity", "small_molecule",
                  "chemical_mixture", "chemical_entity"]

    # List of curie prefixes that are valid for certain curie types
    curie_map = {"disease": ["MONDO", "ORPHANET", "DOID"],
                 "phenotypic_feature": ["HP", "HPO", "EFO"],
                 "gene": ["HGNC", "NCBIGene"],
                 "chemical_substance": ["CHEBI", "PUBCHEM.COMPOUND", "CHEMBL.COMPOUND"],
                 "chemical_mixture": ["CHEBI", "PUBCHEM.COMPOUND", "CHEMBL.COMPOUND"],
                 "chemical_entity": ["CHEBI", "PUBCHEM.COMPOUND", "CHEMBL.COMPOUND"],
                 "small_molecule": ["CHEBI", "PUBCHEM.COMPOUND", "CHEMBL.COMPOUND"],
                 "anatomical_entity": ["UBERON"]}

    def __init__(self, question_graph, source, curie_index=0):

        # List of terms that are going to be connected to make a query
        self.question_graph = question_graph

        # Index in question graph that will be matched against curies
        self.curie_index = curie_index

        # Query source (e.g. /schema or /graph/gamma/quick)
        self.source = source

        # Check to make sure curie index isn't out of range
        if self.curie_index >= len(self.question_graph):
            raise InvalidQueryError(f"Invalid query index ({curie_index})! Question graph only "
                                    f"contains {len(self.question_graph)} entries!")

        # Set the type of the curie for downstream curie checking
        self.curie_type = self.question_graph[self.curie_index]

        # Validate that all entries in question graph are actually valid types
        self.validate_factory()

    def validate_factory(self):
        # Check to make sure all the question types are valid
        for question in self.question_graph:
            if not question in QueryFactory.data_types:
                raise InvalidQueryError(f"Query contains invalid query type: {question}")

    def is_valid_curie(self, curie):
        # Return whether a curie can be used to create a valid query

        # Handle case where curie type has no limitations
        if self.curie_type not in QueryFactory.curie_map:
            return True

        # Otherwise only return true if current query contains one of the acceptable prefixes
        for curie_prefix in QueryFactory.curie_map[self.curie_type]:
            if curie.startswith(curie_prefix):
                return True

        # Curie doesn't start with an acceptable prefix
        return False

    def get_query(self, curie):

        # Return nothing if not valid curie
        if not self.is_valid_curie(curie):
            return None

        question = []
        seen = []
        curie_id = ""
        for i in range(len(self.question_graph)):
            query_type = self.question_graph[i]
            if self.question_graph.count(query_type) > 1:
                # Add alias to beginning of types we've seen before
                alias = f"{query_type[0:3]}{len([x for x in seen if x == query_type])}"
                query = f"{alias}:{query_type}"
            else:
                alias = query_type
                query = query_type

            # Set curie id to the alias if this is the correct index
            if i == self.curie_index:
                curie_id = alias

            # Append to list of query_types currently in query
            seen.append(query_type)
            # Append to list of actual terms that will appear in query
            question.append(query)

        # Build and return query
        return f"select {'->'.join(question)} from '{self.source}' where {curie_id}='{curie}'"
