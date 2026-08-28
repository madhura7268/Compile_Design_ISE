import graphviz

def generate_graphviz_tree(ast_node: dict) -> graphviz.Digraph:
    """
    Recursively builds a Graphviz directed graph from the AST node dictionary
    returned by the parser's to_d3_json() method.
    """
    dot = graphviz.Digraph(comment='Abstract Syntax Tree')
    dot.attr(rankdir='TB')
    
    # Dark theme styling
    dot.attr('node', 
             shape='box', 
             style='rounded,filled', 
             fillcolor='#1E1B4B', 
             color='#4F46E5', 
             fontcolor='white',
             fontname='sans-serif',
             penwidth='2')
    dot.attr('edge', color='#4F46E5', penwidth='1.5', arrowsize='0.8')
    
    node_counter = [0]
    
    def _traverse(node: dict) -> str:
        if not node:
            return ""
            
        current_id = f"n{node_counter[0]}"
        node_counter[0] += 1
        
        node_name = node.get("name", "Unknown")
        dot.node(current_id, node_name)
        
        children = node.get("children", [])
        for child in children:
            child_id = _traverse(child)
            if child_id:
                dot.edge(current_id, child_id)
                
        return current_id

    if ast_node:
        _traverse(ast_node)

    return dot
