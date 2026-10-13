import json
import logging
from typing import Dict, Any, Optional, List
from app.config import settings
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.llm_client import get_llm_client
from app.tools.registry import TOOL_DEFINITIONS, execute_tool
from app.db.repository import Repository
from app.db.models import ToolTraceModel

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    def __init__(self, max_steps: int = settings.max_agent_steps):
        self.max_steps = max_steps
        self.llm_client = get_llm_client()

    def run(
        self,
        user_prompt: str,
        conversation_id: Optional[str] = None,
        user_label: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a full multi-step agent turn with persistence and tool trace recording."""
        cid = Repository.get_or_create_conversation(conversation_id, user_label=user_label)
        Repository.add_message(cid, "user", user_prompt)

        # Build message history for the LLM
        history = Repository.get_messages(cid)
        messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in history:
            messages.append({"role": m.role, "content": m.content})

        collected_traces: List[ToolTraceModel] = []
        final_answer = ""
        steps_taken = 0

        for step in range(1, self.max_steps + 1):
            steps_taken = step
            try:
                turn = self.llm_client.generate_turn(messages, TOOL_DEFINITIONS, step=step)
            except Exception as e:
                logger.error(f"Error during LLM generate_turn on step {step}: {e}")
                final_answer = f"Encountered an internal error processing request: {str(e)}"
                break

            # Handle Tool Calls
            if turn.tool_calls:
                # Add assistant message containing the tool calls to the context
                assistant_tool_msg = {
                    "role": "assistant",
                    "content": turn.content or "",
                    "tool_calls": turn.tool_calls
                }
                messages.append(assistant_tool_msg)

                for tc in turn.tool_calls:
                    fn = tc.get("function", {})
                    tool_name = fn.get("name", "unknown")
                    raw_args = fn.get("arguments", "{}")
                    
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception:
                        args = {"raw": raw_args}

                    # Execute the tool
                    result = execute_tool(
                        name=tool_name,
                        arguments=args,
                        source_conversation_id=cid
                    )
                    ok = not ("error" in result and len(result) == 1)

                    # Persist trace
                    trace = Repository.record_tool_trace(
                        conversation_id=cid,
                        step=step,
                        tool_name=tool_name,
                        args=args,
                        result=result,
                        ok=ok
                    )
                    collected_traces.append(trace)

                    # Append tool result to context
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", f"call_{step}"),
                        "name": tool_name,
                        "content": json.dumps(result)
                    })

                # Continue multi-step loop to process results
                continue

            # Assistant finished and produced final content
            if turn.content:
                final_answer = turn.content
                break

        if not final_answer:
            final_answer = "Maximum reasoning steps reached without completing all requested actions. Please check recent tool traces for intermediate status."

        # Save assistant final response
        Repository.add_message(cid, "assistant", final_answer)

        # Retrieve all traces for this conversation
        all_traces = Repository.get_traces(cid)

        return {
            "conversation_id": cid,
            "answer": final_answer,
            "steps_taken": steps_taken,
            "traces": [t.model_dump() for t in all_traces]
        }
