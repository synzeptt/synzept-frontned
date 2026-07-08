from app.services.time_machine_service import TimeMachineService


def test_time_machine_returns_reflection_and_turning_point_data():
    service = TimeMachineService()

    journey = service.journey()
    turning_points = service.turning_points()
    reflections = service.reflections()
    comparisons = service.compare()
    search_results = service.search("feedback")

    assert journey
    assert turning_points
    assert reflections
    assert comparisons
    assert search_results
