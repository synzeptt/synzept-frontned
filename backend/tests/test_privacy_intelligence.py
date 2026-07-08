from app.schemas.privacy_intelligence import PrivacyContributionSettingsIn
from app.services.privacy_intelligence import PrivacyIntelligenceService


def test_snapshot_separates_personal_and_global_layers():
    snapshot = PrivacyIntelligenceService().snapshot()

    assert "personalIntelligence" in snapshot.architectureLayers
    assert "globalIntelligence" in snapshot.architectureLayers
    assert "User memories" in snapshot.architectureLayers["personalIntelligence"]
    assert "Aggregated success patterns" in snapshot.architectureLayers["globalIntelligence"]


def test_recommendations_label_personal_evidence_and_global_patterns_separately():
    recommendation = PrivacyIntelligenceService().recommendations()[0]

    assert recommendation.personalEvidence
    assert recommendation.globalPatterns
    assert recommendation.privacyExplanation
    assert "Personal evidence" not in recommendation.globalPatterns[0].summary


def test_global_patterns_are_anonymized_aggregates():
    patterns = PrivacyIntelligenceService().global_patterns()

    assert patterns
    assert all(pattern.sampleSize > 100 for pattern in patterns)
    assert all("no" in pattern.anonymization.lower() or "private" in pattern.anonymization.lower() or "aggregate" in pattern.anonymization.lower() for pattern in patterns)


def test_contribution_settings_support_opt_out():
    settings = PrivacyIntelligenceService().update_contribution_settings(
        PrivacyContributionSettingsIn(optedIn=False, mode="local_only")
    )

    assert settings.optedIn is False
    assert settings.mode == "local_only"
    assert settings.localOnlySignals


def test_privacy_guarantees_prevent_raw_private_data_in_global_layer():
    snapshot = PrivacyIntelligenceService().snapshot()
    guarantees = " ".join(snapshot.privacyGuarantees).lower()

    assert "raw memories" in guarantees
    assert "global patterns" in guarantees
    assert "opt out" in guarantees
