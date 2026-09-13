import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LEAD_SOURCE_LABEL, LEAD_STATUS_LABEL, StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("renders French labels for property statuses", () => {
    render(<StatusBadge kind="property" status="pending_review" />);
    expect(screen.getByText("En attente de validation")).toBeInTheDocument();
  });

  it("uses the verified variant for published properties", () => {
    render(<StatusBadge kind="property" status="published" />);
    const badge = screen.getByText("Publié");
    expect(badge).toHaveClass("text-verified");
    expect(badge).toHaveAttribute("data-status", "published");
  });

  it("uses the destructive variant for rejected leads and cancelled bookings", () => {
    render(
      <>
        <StatusBadge kind="lead" status="rejected" />
        <StatusBadge kind="booking" status="cancelled" />
      </>,
    );
    expect(screen.getByText("Rejeté")).toHaveClass("text-destructive");
    expect(screen.getByText("Annulée")).toHaveClass("text-destructive");
  });

  it("renders request, lead and identity labels", () => {
    render(
      <>
        <StatusBadge kind="request" status="accepted" />
        <StatusBadge kind="lead" status="visit_scheduled" />
        <StatusBadge kind="identity" status="approved" />
      </>,
    );
    expect(screen.getByText("Acceptée")).toBeInTheDocument();
    expect(screen.getByText("Visite planifiée")).toBeInTheDocument();
    expect(screen.getByText("Approuvé")).toBeInTheDocument();
  });

  it("exposes lead labels", () => {
    expect(LEAD_STATUS_LABEL.new).toBe("Nouveau");
    expect(LEAD_STATUS_LABEL.contacted).toBe("Contacté");
    expect(LEAD_STATUS_LABEL.converted).toBe("Converti");
    expect(LEAD_SOURCE_LABEL.tayara).toBe("Tayara");
    expect(LEAD_SOURCE_LABEL.manual).toBe("Manuel");
  });
});
