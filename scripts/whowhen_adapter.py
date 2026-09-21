"""Who&When Pro -> JevTrace adapter.

Converts heterogeneous Who&When Pro trajectories (action/agent/round/planning
message kinds across 8 frameworks) into JevTrace normalized state
{task, steps:[{component, status, text, speaker}]} plus mapped labels.

Step construction (deterministic, documented):
  user          -> task context (first user message, truncated)
  action        -> tool_router (generator if is_final_answer), text=reasoning+action+observation
  agent         -> component by ROLE_MAP, speaker=agent name, text=output
  (no kind)+agent_id -> component by ROLE_MAP, speaker=agent_id, text=output
  planning      -> planner
  round         -> planner (multi-agent deliberation), text=turns JSON
  final_answer  -> generator
All statuses are "success" — the trace must not leak label info.

Ground-truth step mapping (framework-specific gt formats -> our 1-based index):
  int (alfagent/smolagents) -> our step sourced from action with that step_number
  "r.p" (magentic-one)      -> our step sourced from agent msg round==r, position==p
  {"round": r} (debate/dylan)-> our step sourced from round msg round==r
  {"stage": s} (metagpt/macnet) -> our step sourced from msg with stage==s
  None                      -> unmappable (skip When, keep Who/Error)

Error-mode mapping (14 modes observed in text split -> 7 JevTrace categories):
  R.1,R.2,R.3 -> hallucination | R.4,PL.1,C.1 -> planning_error
  A.1,A.2 -> tool_failure | A.3,A.4 -> timeout
  V.1,C.2 -> memory_failure | V.2,C.3 -> verification_failure
"""

import json

ROLE_MAP = {
    "orchestrator": "planner",
    "architect": "planner",
    "coder": "generator",
    "engineer": "generator",
    "author": "generator",
    "rewriter": "generator",
    "sink": "generator",
    "assistant": "generator",
    "critic": "verifier",
    "reviewer": "verifier",
    "websurfer": "retriever",
    "filesurfer": "retriever",
    "computerterminal": "tool_router",
    "user_proxy": "tool_router",
}

MODE_TO_CATEGORY = {
    "R.1": "hallucination",
    "R.2": "hallucination",
    "R.3": "hallucination",
    "R.4": "planning_error",
    "PL.1": "planning_error",
    "A.1": "tool_failure",
    "A.2": "tool_failure",
    "A.3": "timeout",
    "A.4": "timeout",
    "V.1": "memory_failure",
    "V.2": "verification_failure",
    "C.1": "planning_error",
    "C.2": "memory_failure",
    "C.3": "verification_failure",
}

TASK_CHARS = 1500
STEP_CHARS = 600


def _cut(s, n):
    s = str(s or "")
    return s[:n]


def convert_record(rec):
    """Returns (state, labels, meta). labels['step'] is our 1-based index or None."""
    traj = json.loads(rec["trajectory"])
    gt = json.loads(rec["ground_truth"])

    task_parts = []
    steps = []  # each: {component, status, text, speaker, src}
    speakers = []

    for m in traj:
        kind = m.get("kind")
        if kind == "user":
            if m.get("content"):
                task_parts.append(str(m["content"]))
            continue
        if kind == "action":
            final = str(m.get("is_final_answer", "")).lower() == "true"
            comp = "generator" if final else "tool_router"
            text = " ".join(
                _cut(m.get(f), 400) for f in ("reasoning", "action", "code", "observation") if m.get(f)
            )
            steps.append({"component": comp, "status": "success", "text": _cut(text, STEP_CHARS),
                          "speaker": None, "src": {"kind": "action", "step_number": m.get("step_number")}})
        elif kind == "agent":
            agent = m.get("agent")
            if agent and agent not in speakers:
                speakers.append(agent)
            comp = ROLE_MAP.get(str(agent or "").lower(), "generator")
            steps.append({"component": comp, "status": "success", "text": _cut(m.get("output"), STEP_CHARS),
                          "speaker": agent, "src": {"kind": "agent", "round": m.get("round"), "position": m.get("position")}})
        elif kind == "planning":
            text = _cut(m.get("content") or m.get("output"), STEP_CHARS)
            steps.append({"component": "planner", "status": "success", "text": text,
                          "speaker": None, "src": {"kind": "planning"}})
        elif kind == "round":
            turns = m.get("turns") or []
            for t in turns:
                aid = (t or {}).get("agent_id")
                if aid and aid not in speakers:
                    speakers.append(aid)
            text = _cut(json.dumps(turns), STEP_CHARS)
            steps.append({"component": "planner", "status": "success", "text": text,
                          "speaker": None, "src": {"kind": "round", "round": m.get("round")}})
        elif kind == "final_answer":
            steps.append({"component": "generator", "status": "success",
                          "text": _cut(m.get("content"), STEP_CHARS),
                          "speaker": None, "src": {"kind": "final_answer"}})
        else:
            # kind None + agent_id (macnet/metagpt/mathchat style)
            agent = m.get("agent_id")
            if agent is None:
                continue
            if agent not in speakers:
                speakers.append(agent)
            comp = ROLE_MAP.get(str(agent).lower(), "generator")
            steps.append({"component": comp, "status": "success", "text": _cut(m.get("output"), STEP_CHARS),
                          "speaker": agent, "src": {"kind": "agent_id", "stage": m.get("stage"),
                                                   "round": m.get("round"), "position": m.get("position")}})

    task_raw = rec.get("task", "")
    try:
        task_json = json.loads(task_raw)
        task_str = task_json.get("query") or task_raw
    except Exception:
        task_str = task_raw
    if task_parts:
        task_str = _cut(task_parts[0], TASK_CHARS)
    else:
        task_str = _cut(task_str, TASK_CHARS)

    state = {"task": task_str,
             "steps": [{"component": s["component"], "status": s["status"], "text": s["text"]} for s in steps]}

    # --- labels ---
    agent = gt.get("agent")
    agents = gt.get("agents") or ([agent] if agent else [])
    step_idx = _map_step(gt, steps)
    labels = {"agent": agent, "agents": agents, "step": step_idx,
              "step_raw": gt.get("step", gt.get("round", gt.get("stage"))),
              "mode": gt.get("mode"), "category": MODE_TO_CATEGORY.get(gt.get("mode"))}
    meta = {"id": rec.get("id"), "framework": rec.get("framework"),
            "benchmark": rec.get("benchmark"), "n_steps": len(steps),
            "speakers": speakers, "step_mappable": step_idx is not None}
    return state, labels, meta


def _map_step(gt, steps):
    """Map framework-specific gt step to our 1-based step index. None if unmappable."""
    s = gt.get("step")
    if isinstance(s, int):
        for i, st in enumerate(steps, start=1):
            if st["src"].get("step_number") == s:
                return i
        return None
    if isinstance(s, str) and "." in s:
        try:
            r, p = s.split(".")
            r, p = int(r), int(p)
        except ValueError:
            return None
        for i, st in enumerate(steps, start=1):
            src = st["src"]
            if src.get("round") == r and src.get("position") == p:
                return i
        return None
    if isinstance(s, float):
        return _map_step({"step": str(s)}, steps)
    if gt.get("round") is not None and s is None and gt.get("agent") is None:
        # debate/dylan: {"agents": [...], "round": r}
        for i, st in enumerate(steps, start=1):
            if st["src"].get("kind") == "round" and st["src"].get("round") == gt["round"]:
                return i
        return None
    if gt.get("stage") is not None:
        # metagpt/macnet: stage -> nth non-user message (0-based stage)
        try:
            idx = int(gt["stage"]) + 1
        except (TypeError, ValueError):
            return None
        n_nonuser = len(steps)
        if 1 <= idx <= n_nonuser:
            # prefer a step whose src stage matches, else positional
            for i, st in enumerate(steps, start=1):
                if st["src"].get("stage") == gt["stage"]:
                    return i
            return idx
        return None
    if gt.get("round") is not None and gt.get("position") is not None:
        # mathchat: {"agent","round","position"}
        for i, st in enumerate(steps, start=1):
            src = st["src"]
            if src.get("round") == gt["round"] and src.get("position") == gt["position"]:
                return i
        return None
    return None
