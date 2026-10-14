import click
import os
from nexus.core.persistence.repository import NexusRepository
from nexus.core.runner.llm import LLMClient
from nexus.core.runner.gemini_client import GeminiLLMClient
from nexus.core.evaluation.suite import CoreSuiteRunner

@click.group()
def cli():
    '''Nexus Agent Evaluation CLI'''
    pass

@cli.command()
@click.option('--scenario', required=True, help="Scenario ID to run")
@click.option('--mode', type=click.Choice(['live', 'replay']), required=True, help="Run mode")
@click.option('--replay-of', help="Source run ID for replay mode")
def run(scenario, mode, replay_of):
    '''Run a scenario evaluation'''
    click.echo(f"Placeholder: Running scenario {scenario} in {mode} mode.")

@cli.command()
@click.option('--suite', required=True, help="Evaluation suite to run")
@click.option('--mode', type=click.Choice(['live', 'replay', 'fake']), default='fake', help="Run mode")
@click.option('--compare', nargs=2, help="Compare two agent versions (e.g., v0.1 v0.2)")
def eval(suite, mode, compare):
    '''Evaluate a suite'''
    repo = NexusRepository("sqlite:///nexus.db")
    
    if mode == "live":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            click.echo("Error: GEMINI_API_KEY must be set for live execution.")
            return
        llm = GeminiLLMClient(api_key=api_key)
    else:
        click.echo("Using Fake LLM Client for offline run...")
        class FallbackFakeLLM:
            def generate(self, prompt):
                return {"action_type": "DECLINE", "public_reason": "UNAVAILABLE", "communication": {"template": "UNAVAILABLE_PROPOSE_ALTERNATIVES"}}, "fake-model"
        llm = FallbackFakeLLM()
        
    runner = CoreSuiteRunner(repo, llm, f"scenarios/{suite}")
    
    if compare:
        v_base, v_cand = compare
        click.echo(f"Running evaluation regression: {v_base} vs {v_cand} on suite {suite}")
        
        summary = runner.compare_suite(baseline_version=v_base, candidate_version=v_cand)
        
        click.echo(f"\n--- NEXUS Regression Report ---")
        click.echo(f"Baseline: {v_base}")
        click.echo(f"Candidate: {v_cand}")
        click.echo(f"")
        click.echo(f"Scenarios: {summary.total_scenarios}")
        click.echo(f"Comparable: {summary.comparable}")
        click.echo(f"Unchanged: {summary.unchanged}")
        click.echo(f"Improved: {summary.improved}")
        click.echo(f"Regressions: {summary.regressions}")
        click.echo(f"Incompatible: {summary.incompatible}")
        click.echo(f"Errors: {summary.errors}")
        
        for res in summary.results:
            click.echo(f"\nScenario: {res.scenario_id}")
            click.echo(f"Status: {res.status.value}")
            if res.status.value == "ERROR" or res.status.value == "INCOMPATIBLE_INPUT":
                click.echo(f"Reason: {res.error_message or res.candidate_failure_code or res.baseline_failure_code}")
                continue
                
            click.echo(f"Baseline result: {res.baseline_status} [{res.baseline_run_id}]")
            click.echo(f"Candidate result: {res.candidate_status} [{res.candidate_run_id}]")
            if res.changed_assertions:
                for diff in res.changed_assertions:
                    click.echo(f"  Changed assertion: {diff.assertion_type}")
                    click.echo(f"  Expected value: {diff.expected_value}")
                    click.echo(f"  Baseline actual: {diff.baseline_actual} (Pass: {diff.baseline_passed})")
                    click.echo(f"  Candidate actual: {diff.candidate_actual} (Pass: {diff.candidate_passed})")
                    
    else:
        click.echo(f"Running evaluation suite: {suite} in {mode} mode")
        summary = runner.run_suite_live(agent_version="v0.1")
        
        click.echo(f"\n--- Suite Summary ---")
        click.echo(f"Total: {summary.total_scenarios}, Passed: {summary.passed_scenarios}, Failed: {summary.failed_scenarios}, Errors: {summary.error_scenarios}")
        
        for res in summary.results:
            click.echo(f"  {res.scenario_id} [{res.run_id}] -> {res.status} (Pass: {res.passed_assertions}/{res.total_assertions}) {res.failure_code or ''} {res.error_message or ''}")
        
if __name__ == '__main__':
    cli()
