from agent import create_sketch_graph

def on_user_input_received(json_data: dict, user_id: str):
    graph = create_sketch_graph()
    state = {
        "user_id": user_id,
        "user_data": json_data,
        "svg_code": None,
        "svg_file_path": None,
        "edit_instructions": None,
        "status": "pending"
    }
    output_state = graph.invoke(state)
    return output_state["svg_file_path"]