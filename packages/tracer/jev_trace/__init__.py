"""jev-trace — one-liner tracer for any agent, LangChain/LangGraph auto.

Usage:
    from jev_trace import JevTrace
    tracer = JevTrace(api_url="http://localhost:8000", task_name="my-agent")
    with tracer.span("retriever", inputs={"query": q}):
        docs = retriever(q)

LangChain:
    from jev_trace.langchain import JevTraceCallbackHandler
    handler = JevTraceCallbackHandler(tracer)
    llm = ChatOpenAI(callbacks=[handler])
"""

from .tracer import JevTrace, COMPONENTS, normalize_component

__all__ = ["JevTrace", "COMPONENTS", "normalize_component"]
