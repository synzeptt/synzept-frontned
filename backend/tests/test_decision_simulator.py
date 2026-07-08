from app.schemas.decision_simulator import FinalChoiceIn, SimulationOutcomeIn
from app.services.decision_simulator import DecisionSimulatorService


def test_simulation_contains_required_input_context():
    simulation = DecisionSimulatorService().list_simulations()[0]
    context = simulation.inputContext

    assert context.decisionId
    assert context.personalKnowledgeSignals
    assert context.decisionGraphConnections
    assert context.goals
    assert context.missions
    assert context.projects
    assert context.memories
    assert context.riskPreference
    assert context.pastOutcomeSignals


def test_scenarios_include_tradeoffs_assumptions_and_outcomes():
    simulation = DecisionSimulatorService().list_simulations()[0]

    assert len(simulation.scenarios) >= 3
    for scenario in simulation.scenarios:
        assert scenario.title
        assert scenario.potentialBenefits
        assert scenario.potentialRisks
        assert scenario.assumptions
        assert 0 <= scenario.confidence <= 1
        assert scenario.bestCaseOutcome
        assert scenario.worstCaseOutcome
        assert scenario.keyUncertainties


def test_comparison_metrics_cover_required_dimensions():
    scenario = DecisionSimulatorService().list_simulations()[0].scenarios[0]
    comparison = scenario.comparison

    assert comparison.effort >= 0
    assert comparison.risk >= 0
    assert comparison.cost >= 0
    assert comparison.time >= 0
    assert comparison.goalAlignment >= 0
    assert comparison.expectedImpact >= 0


def test_record_final_choice_is_mock_and_non_production():
    result = DecisionSimulatorService().record_choice(
        FinalChoiceIn(
            simulationId="sim-memory-feed-home",
            scenarioId="scenario-feed-default",
            rationale="The feed best matches the current retention goal.",
        )
    )

    assert result["status"] == "recorded_mock"
    assert result["recorded"] is True


def test_record_outcome_returns_learning_feedback():
    learning = DecisionSimulatorService().record_outcome(
        SimulationOutcomeIn(
            simulationId="sim-memory-feed-home",
            scenarioId="scenario-workspace-home",
            actualResult="Users liked the broader home but still wanted stronger daily recall.",
            lessonsLearned=["Keep Memory Feed prominent inside Workspace Home."],
        )
    )

    assert learning is not None
    assert learning.accuracy >= 0
    assert learning.lessonsLearned
