from typing import List, TypedDict, Annotated
import operator


class AgentState(TypedDict):
    # Using Annotated with operator .add ensure that messages
    # are appended to the history rather than replace

    messages: Annotated[list[dict], operator.add]
    current_query: str
    documents: List[str]
    plan: List[str]
    status: str
    final_answer: str
