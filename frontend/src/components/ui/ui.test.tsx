import { fireEvent, render, screen } from "@testing-library/react";
import { MotionConfig } from "motion/react";
import { describe, expect, it } from "vitest";

import type { Trail } from "../../lib/api/types";
import { RiskBadge, SeverityBadge } from "./Badges";
import { CountUp } from "./Data";
import { DiffTable, TrailView } from "./Evidence";

describe("SeverityBadge", () => {
  it.each([
    ["critical", "Critical"],
    ["high", "High"],
    ["medium", "Medium"],
    ["low", "Low"],
  ] as const)("shows a shape and the label for %s", (severity, label) => {
    const { container } = render(<SeverityBadge severity={severity} />);
    expect(screen.getByText(label)).toBeInTheDocument();
    expect(container.querySelector("svg")).not.toBeNull();
  });
});

describe("RiskBadge", () => {
  it("always states the confidence next to the level (FR-RSK-002)", () => {
    render(<RiskBadge level="warning" confidence={1} />);
    expect(screen.getByLabelText("Risk Warning, confidence 100%")).toBeInTheDocument();
  });
});

describe("DiffTable", () => {
  it("highlights only rows whose values differ", () => {
    render(
      <DiffTable
        fields={[
          { field: "status", values: { crm: "active", billing: "cancelled" } },
          { field: "plan", values: { crm: "pro", billing: "pro" } },
        ]}
      />,
    );
    expect(screen.getByText("cancelled").className).toContain("bg-peach-bg");
    expect(screen.getAllByText("pro")[0]!.className).not.toContain("bg-peach-bg");
  });
});

describe("TrailView", () => {
  const trail: Trail = {
    facts: [
      { id: "f1", kind: "record_field", system: "crm", external_id: "C-1", record_type: "account", version: 1, field: "status", value: "active", recorded_at: "2026-10-01T00:00:00Z" },
      { id: "f2", kind: "record_field", system: "billing", external_id: "S-1", record_type: "subscription", version: 2, field: "status", value: "cancelled", recorded_at: "2026-10-02T00:00:00Z" },
      { id: "f3", kind: "record_field", system: "support", external_id: "Z-1", record_type: "ticket", version: 1, field: "priority", value: "high", recorded_at: "2026-10-03T00:00:00Z" },
    ],
    inferences: [{ id: "i1", kind: "rule", rule_key: "R004", uses: ["f1", "f2"], statement: "CRM active although Billing cancelled" }],
    conclusion: { kind: "finding", rule_key: "R004", risk: "high", confidence: 0.829, uses: ["i1"] },
  };

  it("groups facts, inferences and the conclusion separately", () => {
    render(<TrailView trail={trail} />);
    expect(screen.getByText("Facts (from source systems)")).toBeInTheDocument();
    expect(screen.getByText("What RealitySync inferred")).toBeInTheDocument();
    expect(screen.getByText("Conclusion")).toBeInTheDocument();
  });

  it("pinning an inference highlights exactly the facts it uses", () => {
    render(<TrailView trail={trail} />);
    fireEvent.click(screen.getByText("CRM active although Billing cancelled").closest("button")!);
    const tile = (text: string) => screen.getByText(text).closest("button")!;
    expect(tile("f1").className).toContain("border-ink-950");
    expect(tile("f2").className).toContain("border-ink-950");
    expect(tile("f3").className).not.toContain("border-ink-950");
  });
});

describe("CountUp", () => {
  it("shows the final value immediately under reduced motion", () => {
    render(
      <MotionConfig reducedMotion="always">
        <CountUp value={62} animate />
      </MotionConfig>,
    );
    expect(screen.getAllByText("62").length).toBeGreaterThan(0);
  });
});
