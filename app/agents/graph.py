import logfire
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.state import AgentState
from app.agents.nodes.planner import planner_node
from app.agents.nodes.responder import generate_node
from app.agents.nodes.retriever import retrieve_node


# 1. Initialize the State Graph
workflow = StateGraph(AgentState)

workflow.add_node("planner",planner_node)
workflow.add_node('retriever',retrieve_node)
workflow.add_node('responder',generate_node)

# 3. Define the Edges & Routing Logic
def route_planner(state: AgentState):
    """
    Routes the workflow based on the planner's decision.
    """
    if state['current_query'] == "CONVERSATIONAL":
        return "responder"
    return 'retriever'


workflow.set_entry_point("planner")
workflow.add_conditional_edges(
    "planner",
    route_planner,
    {
        "retriever":"retriever",
        "responder":"responder"
    }
)

workflow.add_edge("retriever","responder")
workflow.add_edge('responder',END)


# -- HYBRID MEMORY UPGRADE ---

def get_checkpointer():
    """
    Returns a persistent Postgres checkpointer in Cloud/Production mode,
    add falls back to in-memory checkpointer in Local Mode.
    """

    from app.config import settings

    if settings.LOCAL_MODE:
        from langgraph.checkpoint.memory import MemorySaver
        print("🗃️ Using Local MemorySaver (RAM)")
        return MemorySaver()
    
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg_pool import ConnectionPool

        conninfo = f"postgresql://{settings.DB_USER}:{settings.DB_PASS}@/{settings.DB_NAME}?host=/cloudsql/{settings.DB_CONNECTION_NAME}"

        # initialize the pool

        pool = ConnectionPool(configure=conninfo, max_size=10)

        with pool.connection() as conn:
            checkpointer = PostgresSaver(conn)
            checkpointer.setup()

        logfire.info("🐘 Using Persistent PostgresSaver (Cloud SQL Pool)")
        return PostgresSaver(pool)
    
    except Exception as e:
        from langgraph.checkpoint.memory import MemorySaver
        logfire.error(f"⚠️ Postgress connection Failed: {e}. Failing back to Memoryserver.")
        return MemorySaver()



# --- MEMORY UPGRADE ---
# MemorySaver allows the agent to remember conversations based on "there memory"

checkpointer = get_checkpointer()

# 4. Compile the Graph with Memory
rag_agent = workflow.compile(checkpointer=checkpointer)
