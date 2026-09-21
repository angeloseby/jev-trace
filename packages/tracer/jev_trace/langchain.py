"""LangChain/LangGraph integration — callback handler that auto-captures steps."""

from typing import Any

try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.outputs import LLMResult
except Exception:  # graceful if langchain not installed
    BaseCallbackHandler = object  # type: ignore
    LLMResult = Any  # type: ignore


class JevTraceCallbackHandler(BaseCallbackHandler):  # type: ignore
    """Drop into any LangChain LLM/Chain/Agent to auto-trace.

    Usage:
        from jev_trace import JevTrace
        from jev_trace.langchain import JevTraceCallbackHandler
        tracer = JevTrace(api_url="http://localhost:8000", task_name="langchain-agent")
        handler = JevTraceCallbackHandler(tracer)
        llm = ChatOpenAI(callbacks=[handler])
        chain = prompt | llm  # any Runnable
        result = chain.invoke({"input": "…"}, config={"callbacks": [handler]})
        tracer.complete("completed")
        tracer.analyze()  # optional: triggers Jev
    """

    def __init__(self, tracer):
        self.tracer = tracer

    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        self.tracer._post_step("generator", "success", {"prompts": prompts[:1]}, {}, None)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        pass

    def on_retriever_start(self, serialized: dict[str, Any], query: str, **kwargs: Any) -> None:
        self.tracer._post_step("retriever", "success", {"query": query}, {}, None)

    def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kwargs: Any) -> None:
        name = (serialized or {}).get("name") or (serialized or {}).get("id") or "tool"
        self.tracer._post_step("tool_router", "success", {"tool": name, "input": input_str[:500]}, {}, None)

    def on_chain_start(self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any) -> None:
        name = (serialized or {}).get("name") or "chain"
        if "planner" in name.lower() or "plan" in name.lower():
            self.tracer._post_step("planner", "success", {"chain": name}, {}, None)

    def on_agent_action(self, action: Any, **kwargs: Any) -> None:
        tool = getattr(action, "tool", "") or ""
        self.tracer._post_step("tool_router", "success", {"tool": tool}, {}, None)

    def on_agent_finish(self, finish: Any, **kwargs: Any) -> None:
        pass
