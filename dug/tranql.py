import json


class MissingNodeReferenceError(BaseException):
    pass


class MissingEdgeReferenceError(BaseException):
    pass


class QueryKG:
    def __init__(self, kg_json):
        self.kg = kg_json
        self.answers = kg_json.get('knowledge_map', [])
        self.question = kg_json["question_graph"]
        self.nodes = {node["id"]: node for node in kg_json.get('knowledge_graph', {}).get('nodes', [])}
        self.edges = {edge["id"]: edge for edge in kg_json.get('knowledge_graph', {}).get('edges', [])}

    def get_answer_subgraph(self, answer, include_node_keys=[], include_edge_keys=[]):

        # Get answer nodes
        answer_nodes = []
        for binding_id, binding_nodes in answer["node_bindings"].items():
            # Add node info for each node included in answer graph
            for answer_node in binding_nodes:
                # Throw error if node doesn't actually exist in 'nodes' section of knowledge graph
                if answer_node not in self.nodes:
                    err_msg = f"Unable to assemble subraph for answer:\n{json.dumps(answer, indent=2)}\n" \
                        f"Parent graph doesn't contain node info for: {answer_node}"
                    raise MissingNodeReferenceError(err_msg)

                # Add only node info that you actually want
                answer_nodes.append(self.get_node(answer_node, include_node_keys))

        # Get answer edges
        answer_edges = []
        for binding_id, binding_edges in answer["edge_bindings"].items():
            # Add edge info for each edge included in answer graph
            for answer_edge in binding_edges:
                # Throw error if edge doesn't actually exist in 'edges' section of knowledge graph
                if answer_edge not in self.edges:
                    err_msg = f"Unable to assemble subraph for answer:\n{json.dumps(answer, indent=2)}\n" \
                        f"Parent graph doesn't contain edge info for: {answer_edge}"
                    raise MissingEdgeReferenceError(err_msg)

                # Add only information from edge that you actually want
                answer_edges.append(self.get_edge(answer_edge, include_edge_keys))

        kg = {"knowledge_graph": {"nodes": answer_nodes,
                                  "edges": answer_edges},
              "knowledge_map": [answer],
              "question_graph": self.question}

        return QueryKG(kg)

    def get_node(self, node_id, include_node_keys=[]):
        # Return node with optionally subsetted information
        node = self.nodes[node_id]

        # Optionally subset to get only certain information columns
        if include_node_keys:
            node = {key: node[key] for key in include_node_keys}
        return node

    def get_edge(self, edge_id, include_edge_keys=[]):
        # Return edge with optionally subsetted information
        edge = self.edges[edge_id]

        # Optionally subset to include only certain info
        if include_edge_keys:
            edge = {key: edge[key] for key in include_edge_keys}
        return edge

    def get_node_names(self, include_curie=True):
        node_names = []
        curie_ids = self.get_curie_ids()
        for node in self.kg.get('knowledge_graph', {}).get('nodes', []):
            if include_curie or node['id'] not in curie_ids:
                node_names.append(node['name'])
        return node_names

    def get_node_synonyms(self, include_curie=True):
        node_synonyms = []
        curie_ids = self.get_curie_ids()
        for node in self.kg.get('knowledge_graph', {}).get('nodes', []):
            if include_curie or node['id'] not in curie_ids:
                node_synonyms += node.get('synonyms', [])
        return node_synonyms

    def get_curie_ids(self):
        return [node['curie'] for node in self.question.get('nodes', []) if 'curie' in node]

    def get_kg(self):
        # Parse out the KG in whatever form we want
        # TODO: Make this parse out old-style json so ui doesn't break
        return self.kg


class InvalidQueryError(BaseException):
    pass


class QueryFactory:

    # Class member list of valid data types that can be included in query
    data_types = ["phenotypic_feature", "gene", "disease", "chemical_substance",
                  "drug_exposure", "biological_process", "anatomical_entity"]

    # List of curie prefixes that are valid for certain curie types
    curie_map = {"disease": ["MONDO", "ORPHANET", "DOID"],
                 "phenotypic_feature": ["HP", "HPO", "EFO"],
                 "gene": ["HGNC", "NCBIGene"],
                 "chemical_substance": ["CHEBI", "PUBCHEM"],
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
