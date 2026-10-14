from nexus.core.domain.scenario import Scenario
from nexus.core.scheduling.models import SchedulingConstraints

class MissingSchedulingConstraintsError(Exception):
    pass

class ScenarioSchedulingAdapter:
    '''
    Adapter to derive SchedulingConstraints from a Scenario.
    
    The frozen NEXUS v0.1 Scenario model genuinely lacks a dedicated 
    SchedulingConstraints field. This adapter requires them explicitly 
    in the event payload rather than inventing hidden defaults.
    '''
    
    @staticmethod
    def extract_constraints(scenario: Scenario) -> SchedulingConstraints:
        if scenario.events:
            for event in scenario.events:
                if event.payload and "scheduling_constraints" in event.payload:
                    return SchedulingConstraints(**event.payload["scheduling_constraints"])
                    
        raise MissingSchedulingConstraintsError(
            "Scenario does not explicitly define 'scheduling_constraints' in its events payload. "
            "Hidden defaults (like 7 days) are strictly prohibited."
        )
