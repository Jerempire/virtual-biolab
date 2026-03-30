"""
Protocol Writer Agent for Virtual Biolab

Generates wet lab protocols ready for submission to GenScript (synthesis)
and CRO/core facilities (binding assays).

USAGE:
  from agents.protocol_writer import ProtocolWriter
  writer = ProtocolWriter.from_config("config.yaml")
  protocol = writer.generate("VAGSAF", "ERAP2")
  protocol.save("outputs/protocols/")
"""

import sys
import json
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Protocol:
    """Complete wet lab protocol package."""
    candidate: str
    target: str
    timestamp: str = ""
    synthesis_spec: dict = field(default_factory=dict)
    binding_assay: dict = field(default_factory=dict)
    selectivity_assay: dict = field(default_factory=dict)
    success_criteria: list[str] = field(default_factory=list)
    timeline: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def print_summary(self):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

        print(f"\n{'='*60}")
        print(f"PROTOCOL PACKAGE: {self.candidate} -> {self.target}")
        print(f"Generated: {self.timestamp}")
        print(f"{'='*60}")

        print("\n  [SYNTHESIS SPECIFICATION]")
        for k, v in self.synthesis_spec.items():
            print(f"    {k}: {v}")

        print("\n  [BINDING ASSAY]")
        for k, v in self.binding_assay.items():
            if isinstance(v, list):
                print(f"    {k}:")
                for item in v:
                    print(f"      - {item}")
            else:
                print(f"    {k}: {v}")

        print("\n  [SELECTIVITY COUNTER-SCREEN]")
        for k, v in self.selectivity_assay.items():
            if isinstance(v, list):
                print(f"    {k}:")
                for item in v:
                    print(f"      - {item}")
            else:
                print(f"    {k}: {v}")

        print("\n  [SUCCESS CRITERIA]")
        for sc in self.success_criteria:
            print(f"    - {sc}")

        print("\n  [TIMELINE]")
        for phase, duration in self.timeline.items():
            print(f"    {phase}: {duration}")

        print(f"{'='*60}\n")

    def to_dict(self) -> dict:
        return {
            "candidate": self.candidate,
            "target": self.target,
            "timestamp": self.timestamp,
            "synthesis_spec": self.synthesis_spec,
            "binding_assay": self.binding_assay,
            "selectivity_assay": self.selectivity_assay,
            "success_criteria": self.success_criteria,
            "timeline": self.timeline,
        }

    def save(self, output_dir: str | Path) -> tuple[Path, Path]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        slug = f"{self.candidate}_{self.target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        json_path = out / f"protocol_{slug}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        md_path = out / f"protocol_{slug}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self._to_markdown())

        return json_path, md_path

    def _to_markdown(self) -> str:
        lines = [
            f"# Wet Lab Protocol: {self.candidate} -> {self.target}",
            f"**Generated:** {self.timestamp}",
            "",
            "## 1. Peptide Synthesis Specification",
            "",
            "| Parameter | Value |",
            "|-----------|-------|",
        ]
        for k, v in self.synthesis_spec.items():
            lines.append(f"| {k} | {v} |")

        lines.extend([
            "",
            "## 2. Primary Binding Assay",
            "",
        ])
        for k, v in self.binding_assay.items():
            if isinstance(v, list):
                lines.append(f"**{k}:**")
                for item in v:
                    lines.append(f"- {item}")
            else:
                lines.append(f"**{k}:** {v}")

        lines.extend([
            "",
            "## 3. Selectivity Counter-Screen",
            "",
        ])
        for k, v in self.selectivity_assay.items():
            if isinstance(v, list):
                lines.append(f"**{k}:**")
                for item in v:
                    lines.append(f"- {item}")
            else:
                lines.append(f"**{k}:** {v}")

        lines.extend([
            "",
            "## 4. Success Criteria",
            "",
        ])
        for sc in self.success_criteria:
            lines.append(f"- {sc}")

        lines.extend([
            "",
            "## 5. Timeline",
            "",
            "| Phase | Duration |",
            "|-------|----------|",
        ])
        for phase, duration in self.timeline.items():
            lines.append(f"| {phase} | {duration} |")

        return "\n".join(lines)


class ProtocolWriter:
    """Generates wet lab protocol packages for peptide candidates."""

    def __init__(self, config: dict):
        self.config = config
        self.budget = config.get("crowdfund", {})
        self.primary = config.get("primary_target", {})

    @classmethod
    def from_config(cls, config_path: str = "config.yaml") -> "ProtocolWriter":
        config_file = PROJECT_ROOT / config_path
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return cls(config)

    def generate(self, candidate: str, target: str) -> Protocol:
        """Generate a complete protocol package."""
        candidate = candidate.upper().strip()
        off_targets = self.primary.get("selectivity_targets", {}).get("off_targets", ["ERAP1", "IRAP"])

        protocol = Protocol(
            candidate=candidate,
            target=target,
            synthesis_spec={
                "Sequence": candidate,
                "Length": f"{len(candidate)} residues",
                "N-terminal modification": "Acetylation (Ac-)",
                "C-terminal modification": "Amidation (-NH2)",
                "Purity": ">95% by HPLC",
                "Quantity": "5 mg",
                "Form": "Lyophilized TFA salt",
                "Vendor": "GenScript (recommended) or CPC Scientific",
                "Scrambled control": self._scramble(candidate),
                "Control purity": ">95% by HPLC",
                "Control quantity": "5 mg",
                "QC documentation": "HPLC trace + MS confirmation required",
            },
            binding_assay={
                "Assay type": "Fluorescence polarization (FP) enzymatic activity assay",
                "Target protein": f"Recombinant human {target} (R&D Systems #3830-ZN or equivalent)",
                "Substrate": "L-Leucine-7-amido-4-methylcoumarin (L-AMC) fluorogenic substrate",
                "Readout": f"Inhibition of {target} aminopeptidase activity",
                "Concentrations": "12-point dose-response: 100 uM to 0.003 uM (3-fold dilutions)",
                "Replicates": "Triplicate per concentration",
                "Positive control": "DG013A (known ERAP1/ERAP2 dual inhibitor) if available",
                "Negative control": f"Scrambled peptide ({self._scramble(candidate)})",
                "Vehicle control": "DMSO (match final concentration, max 1%)",
                "Buffer": "50 mM Tris-HCl pH 7.5, 150 mM NaCl",
                "Temperature": "37C",
                "Incubation": "30 min pre-incubation with peptide, then add substrate",
                "Detection": "Excitation 380 nm / Emission 460 nm",
                "Analysis": [
                    "Plot % inhibition vs log[concentration]",
                    "Fit 4-parameter logistic curve (Hill equation)",
                    "Report IC50 with 95% confidence interval",
                    "Report Hill coefficient",
                    "Z-factor for assay quality (must be > 0.5)",
                ],
            },
            selectivity_assay={
                "Purpose": f"Confirm selectivity of {candidate} for {target} over {', '.join(off_targets)}",
                "Off-target proteins": [
                    "Recombinant human ERAP1 (R&D Systems #2334-ZN or equivalent)",
                    "Recombinant human IRAP/LNPEP (R&D Systems or Sigma)",
                ],
                "Assay": "Same FP enzymatic activity assay as primary",
                "Concentrations": "8-point dose-response: 100 uM to 0.01 uM (3-fold dilutions)",
                "Replicates": "Triplicate per concentration",
                "Analysis": [
                    "IC50 determination for each off-target",
                    f"Selectivity ratio = IC50(off-target) / IC50({target})",
                    "Report selectivity ratio with confidence intervals",
                ],
            },
            success_criteria=[
                f"{candidate} IC50 < 10 uM against {target}",
                f"{candidate} IC50 > 100 uM against ERAP1 (selectivity ratio > 10x)",
                f"{candidate} IC50 > 100 uM against IRAP (selectivity ratio > 10x)",
                f"Scrambled control ({self._scramble(candidate)}) IC50 > 1 mM against {target}",
                "Z-factor > 0.5 for all assay plates",
                "All controls behave as expected",
            ],
            timeline={
                "Peptide synthesis + QC": "2-3 weeks",
                "Reagent ordering (recombinant proteins, substrates)": "1 week (parallel with synthesis)",
                "Primary binding assay": "3-5 days",
                "Selectivity counter-screen": "3-5 days",
                "Data analysis + report": "3-5 days",
                "Total": "5-7 weeks from order to final report",
            },
        )

        return protocol

    def _scramble(self, seq: str) -> str:
        """Generate a deterministic scrambled control sequence."""
        # Simple reversal + shift for deterministic scrambling
        chars = list(seq)
        n = len(chars)
        # Reverse, then rotate by 1
        chars = chars[::-1]
        chars = chars[1:] + chars[:1]
        scrambled = "".join(chars)
        # Ensure it's different from original
        if scrambled == seq:
            chars[0], chars[-1] = chars[-1], chars[0]
            scrambled = "".join(chars)
        return scrambled


# ── CLI entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    candidate = sys.argv[1] if len(sys.argv) > 1 else "VAGSAF"
    target = sys.argv[2] if len(sys.argv) > 2 else "ERAP2"

    writer = ProtocolWriter.from_config()
    protocol = writer.generate(candidate, target)
    protocol.print_summary()

    out_dir = PROJECT_ROOT / "outputs" / "protocols"
    json_path, md_path = protocol.save(out_dir)
    print(f"Saved: {json_path}")
    print(f"Saved: {md_path}")
