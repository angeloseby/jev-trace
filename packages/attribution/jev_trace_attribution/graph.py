def build_graph(weights: dict[str, float]) -> dict:
    nodes = [{"id": k, "weight": float(v)} for k, v in weights.items()]
    edges = [{"source": nodes[i]["id"], "target": nodes[i + 1]["id"]} for i in range(len(nodes) - 1)]
    return {"nodes": nodes, "edges": edges}
