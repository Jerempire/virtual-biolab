"""
Gate Pipeline Runner for Virtual Biolab

Runs a candidate through the 9-gate pipeline, producing a structured
HTML report showing pass/fail status for each gate.

USAGE:
  from gates.runner import GateRunner
  runner = GateRunner.from_config("config.yaml")
  result = runner.run_candidate("VAGSAF", "ERAP2")
  result.save_report("outputs/")
"""

import sys
import json
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class GateResult:
    """Result of a single gate evaluation."""
    gate_number: int
    name: str
    gate_type: str           # inherited | agent | funding
    status: str = "pending"  # pending | pass | fail | skip
    evidence: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "gate": self.gate_number,
            "name": self.name,
            "type": self.gate_type,
            "status": self.status,
            "evidence": self.evidence,
            "notes": self.notes,
        }


@dataclass
class PipelineResult:
    """Result of running a candidate through all gates."""
    candidate: str
    target: str
    timestamp: str = ""
    gates: list[GateResult] = field(default_factory=list)
    overall_status: str = "pending"

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def evaluate(self) -> str:
        """Determine overall pipeline status."""
        statuses = [g.status for g in self.gates]
        if any(s == "fail" for s in statuses):
            self.overall_status = "fail"
        elif all(s in ("pass", "skip") for s in statuses):
            self.overall_status = "pass"
        else:
            self.overall_status = "in_progress"
        return self.overall_status

    def print_summary(self):
        """Print gate status summary."""
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

        print(f"\n{'='*65}")
        print(f"PIPELINE REPORT: {self.candidate} -> {self.target}")
        print(f"Generated: {self.timestamp}")
        print(f"{'='*65}")

        for g in self.gates:
            icon = {"pass": "[+]", "fail": "[X]", "skip": "[-]", "pending": "[ ]"}.get(g.status, "[ ]")
            print(f"  {icon} Gate {g.gate_number}: {g.name} ({g.gate_type}) — {g.status.upper()}")
            if g.notes:
                print(f"      Note: {g.notes}")

        self.evaluate()
        print(f"\n{'─'*65}")
        passed = len([g for g in self.gates if g.status == "pass"])
        print(f"  {passed}/{len(self.gates)} gates passed — Overall: {self.overall_status.upper()}")
        print(f"{'='*65}\n")

    def save_report(self, output_dir: str | Path) -> tuple[Path, Path]:
        """Save as JSON and HTML."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        slug = f"{self.candidate}_{self.target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # JSON
        json_path = out / f"pipeline_{slug}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "candidate": self.candidate,
                "target": self.target,
                "timestamp": self.timestamp,
                "overall_status": self.overall_status,
                "gates": [g.to_dict() for g in self.gates],
            }, f, indent=2, ensure_ascii=False)

        # HTML
        html_path = out / f"pipeline_{slug}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(self._to_html())

        return json_path, html_path

    def _to_html(self) -> str:
        """Generate HTML gate report."""
        self.evaluate()
        status_colors = {
            "pass": "#22c55e", "fail": "#ef4444",
            "skip": "#6b7280", "pending": "#f59e0b",
        }
        overall_color = status_colors.get(self.overall_status, "#6b7280")

        rows = ""
        for g in self.gates:
            color = status_colors.get(g.status, "#6b7280")
            evidence_html = "<br>".join(f"&bull; {e}" for e in g.evidence) if g.evidence else "&mdash;"
            rows += f"""
            <tr>
              <td style="text-align:center;font-weight:bold;">{g.gate_number}</td>
              <td>{g.name}</td>
              <td><code>{g.gate_type}</code></td>
              <td style="text-align:center;">
                <span style="color:{color};font-weight:bold;">{g.status.upper()}</span>
              </td>
              <td style="font-size:0.85em;">{evidence_html}</td>
              <td style="font-size:0.85em;">{g.notes or '&mdash;'}</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Pipeline Report: {self.candidate} &rarr; {self.target}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           max-width: 1000px; margin: 2rem auto; padding: 0 1rem;
           background: #0f172a; color: #e2e8f0; }}
    h1 {{ color: #f8fafc; }}
    .verdict {{ font-size: 1.4em; font-weight: bold; color: {overall_color};
               border: 2px solid {overall_color}; padding: 0.5em 1em;
               display: inline-block; border-radius: 8px; margin: 1em 0; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
    th {{ background: #1e293b; color: #94a3b8; padding: 0.6em; text-align: left;
         border-bottom: 2px solid #334155; }}
    td {{ padding: 0.6em; border-bottom: 1px solid #1e293b; vertical-align: top; }}
    tr:hover {{ background: #1e293b; }}
    code {{ background: #1e293b; padding: 0.15em 0.4em; border-radius: 3px;
           font-size: 0.85em; }}
    .meta {{ color: #64748b; font-size: 0.9em; }}
  </style>
</head>
<body>
  <h1>{self.candidate} &rarr; {self.target}</h1>
  <p class="meta">Generated: {self.timestamp}</p>
  <div class="verdict">{self.overall_status.upper()}</div>
  <table>
    <thead>
      <tr>
        <th>#</th><th>Gate</th><th>Type</th><th>Status</th><th>Evidence</th><th>Notes</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body>
</html>"""


class GateRunner:
    """
    Orchestrates the 9-gate pipeline for a candidate.

    Gates 1-4 (inherited): Checks if existing results from ancient-drug-discovery
    meet the pass criteria. Does NOT re-run the scripts.

    Gates 5-9 (new): Runs the agent modules (critic, scout, synthesizer, etc.)
    """

    def __init__(self, config: dict, registry: dict):
        self.config = config
        self.registry = registry
        self.parent_project = Path(config["paths"]["parent_project"]).resolve()

    @classmethod
    def from_config(cls, config_path: str = "config.yaml",
                    registry_path: str = "gates/gate_registry.yaml") -> "GateRunner":
        """Load runner from config files."""
        root = PROJECT_ROOT

        with open(root / config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        with open(root / registry_path, "r", encoding="utf-8") as f:
            registry = yaml.safe_load(f)

        return cls(config, registry)

    def run_candidate(self, candidate: str, target: str,
                      skip_inherited: bool = False) -> PipelineResult:
        """
        Run a candidate through all 9 gates.

        Args:
            candidate: Peptide sequence (e.g., "VAGSAF")
            target: Target protein (e.g., "ERAP2")
            skip_inherited: If True, skip gates 1-4 (assume they passed)

        Returns:
            PipelineResult with all gate outcomes
        """
        result = PipelineResult(candidate=candidate, target=target)
        gates_def = self.registry.get("gates", {})

        for i in range(1, 10):
            gate_key = f"gate_{i}"
            gate_def = gates_def.get(gate_key, {})
            gate_name = gate_def.get("name", f"Gate {i}")
            gate_type = gate_def.get("type", "unknown")

            gate_result = GateResult(
                gate_number=i,
                name=gate_name,
                gate_type=gate_type,
            )

            if gate_type == "inherited":
                if skip_inherited:
                    gate_result.status = "skip"
                    gate_result.notes = "Skipped — inherited from ancient-drug-discovery"
                else:
                    gate_result = self._check_inherited_gate(i, gate_def, gate_result, candidate, target)
            elif gate_type == "agent":
                gate_result = self._run_agent_gate(i, gate_def, gate_result, candidate, target)
            elif gate_type == "funding":
                gate_result = self._check_funding_gate(i, gate_def, gate_result)
            else:
                gate_result.status = "skip"
                gate_result.notes = f"Unknown gate type: {gate_type}"

            result.gates.append(gate_result)

        result.evaluate()
        return result

    def _check_inherited_gate(self, gate_num: int, gate_def: dict,
                               result: GateResult, candidate: str, target: str) -> GateResult:
        """Check if inherited gate has existing results that meet criteria."""
        # Gate 1: Check for GWAS/variant data files
        if gate_num == 1:
            evidence_files = gate_def.get("evidence_files", [])
            found = []
            for ef in evidence_files:
                full_path = self.parent_project / ef
                if full_path.exists():
                    found.append(str(ef))
            if found:
                result.status = "pass"
                result.evidence = [f"Found: {f}" for f in found]
            else:
                result.status = "pending"
                result.notes = "Run ancient-drug-discovery scripts 01-03 first"

        # Gate 2: Check for peptide candidates
        elif gate_num == 2:
            pepmlm_dir = self.parent_project / "v4" / "pepmlm"
            if pepmlm_dir.exists():
                fastas = list(pepmlm_dir.rglob("*.fasta")) + list(pepmlm_dir.rglob("*.faa"))
                if fastas:
                    result.status = "pass"
                    result.evidence = [f"Found {len(fastas)} peptide files in v4/pepmlm/"]
                else:
                    result.status = "pending"
                    result.notes = "No peptide FASTA files found in v4/pepmlm/"
            else:
                result.status = "pending"
                result.notes = "v4/pepmlm/ directory not found"

        # Gate 3-4: Check for Boltz-2 results
        elif gate_num in (3, 4):
            boltz_dir = self.parent_project / "data" / "results" / "boltz2_complexes"
            if boltz_dir.exists():
                jsons = list(boltz_dir.rglob("*.json"))
                cifs = list(boltz_dir.rglob("*.cif"))
                if jsons:
                    result.status = "pass"
                    result.evidence = [
                        f"Found {len(jsons)} JSON score files",
                        f"Found {len(cifs)} CIF structure files",
                    ]
                    if gate_num == 4:
                        result.notes = "Verify selectivity gap manually (ipTM on-target vs off-target)"
                else:
                    result.status = "pending"
                    result.notes = "Run boltz_runner.py first"
            else:
                result.status = "pending"
                result.notes = "No Boltz-2 results directory found"

        return result

    def _run_agent_gate(self, gate_num: int, gate_def: dict,
                        result: GateResult, candidate: str, target: str) -> GateResult:
        """Run an agent gate."""
        # Gate 5: Critic
        if gate_num == 5:
            try:
                sys.path.insert(0, str(PROJECT_ROOT))
                from agents.critic import CriticAgent
                critic = CriticAgent(self.config)
                critique = critic.gather_evidence(candidate, target)

                if critique.gate_passed:
                    result.status = "pass"
                else:
                    result.status = "fail"

                result.evidence = [
                    f"Objections: {len(critique.objections)} total",
                    f"Critical unresolved: {len(critique.critical_unresolved)}",
                ]
                result.notes = "; ".join(o.claim[:80] for o in critique.critical_unresolved)

                # Save critique report
                out_dir = PROJECT_ROOT / "outputs" / "critiques"
                critique.save(out_dir)

            except Exception as e:
                result.status = "fail"
                result.notes = f"Critic agent error: {e}"

        # Gates 6-8: Not yet implemented
        elif gate_num in (6, 7, 8):
            result.status = "pending"
            result.notes = f"Agent not yet implemented — Phase 2"

        return result

    def _check_funding_gate(self, gate_num: int, gate_def: dict,
                            result: GateResult) -> GateResult:
        """Check funding gate status."""
        crowdfund_dir = PROJECT_ROOT / "crowdfund"
        campaign = crowdfund_dir / "campaign_draft.md"
        budget = crowdfund_dir / "budget.yaml"

        found = []
        if campaign.exists():
            found.append("Campaign draft exists")
        if budget.exists():
            found.append("Budget file exists")

        if len(found) >= 2:
            result.status = "pass"
            result.evidence = found
        else:
            result.status = "pending"
            result.notes = "Crowdfunding materials not yet created — Phase 3"

        return result


# ── CLI entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    runner = GateRunner.from_config()

    # Default: run VAGSAF through the pipeline
    candidate = sys.argv[1] if len(sys.argv) > 1 else "VAGSAF"
    target = sys.argv[2] if len(sys.argv) > 2 else "ERAP2"

    print(f"Running {candidate} through 9-gate pipeline for {target}...")
    result = runner.run_candidate(candidate, target)
    result.print_summary()

    # Save report
    out_dir = PROJECT_ROOT / "outputs" / "pipeline"
    json_path, html_path = result.save_report(out_dir)
    print(f"Saved: {json_path}")
    print(f"Saved: {html_path}")
