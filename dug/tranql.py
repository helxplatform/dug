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


