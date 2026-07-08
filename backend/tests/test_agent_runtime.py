from app.agents.runtime import AgentRuntime


def test_agent_runtime_lists_agents_and_plans():
    runtime = AgentRuntime()
    agents = runtime.list_agents()
    plan = runtime.plan(agents[0].id)

    assert agents
    assert plan["status"] == "planned"
