import Modal from "../ui/Modal";
import { formatCurrency } from "../../utils/format";

export default function NegotiationModal({ open, onClose, result, loading }) {
  return (
    <Modal open={open} onClose={onClose} title="Negotiation Complete" wide>
      {loading && (
        <p className="text-muted">Running 4-round AI negotiation...</p>
      )}
      {result && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-xl border border-border bg-background p-4">
              <p className="text-sm text-muted">Agreed Price</p>
              <p className="text-xl font-bold text-primary">{formatCurrency(result.agreed_price)}</p>
            </div>
            <div className="rounded-xl border border-border bg-background p-4">
              <p className="text-sm text-muted">Technician</p>
              <p className="text-xl font-bold">{result.technician_name}</p>
            </div>
            <div className="rounded-xl border border-border bg-background p-4">
              <p className="text-sm text-muted">Status</p>
              <p className="text-xl font-bold capitalize">{result.status}</p>
            </div>
          </div>
          <div className="space-y-3">
            <h3 className="font-semibold text-foreground">Negotiation Rounds</h3>
            {(result.rounds || []).map((round) => (
              <div
                key={round.round}
                className="rounded-xl border border-border bg-background p-4 text-sm"
              >
                <p className="mb-2 font-medium text-foreground">Round {round.round}</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <p className="text-primary">Customer: {formatCurrency(round.customer_offer)}</p>
                    <p className="text-muted">{round.customer_message}</p>
                  </div>
                  <div>
                    <p className="text-secondary">Technician: {formatCurrency(round.tech_offer)}</p>
                    <p className="text-muted">{round.tech_message}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </Modal>
  );
}
