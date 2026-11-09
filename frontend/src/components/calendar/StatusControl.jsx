const OPTIONS = [
  { value: "unpaid", label: "Unpaid" },
  { value: "paid_pending", label: "Paid – not withdrawn" },
  { value: "paid_cleared", label: "Paid – cleared" },
];

/** Three-way status picker for one bill due date, built on native radio buttons. */
export default function StatusControl({ occurrence, disabled, onChange }) {
  const name = `status-${occurrence.bill_id}-${occurrence.due_date}`;

  return (
    <fieldset className="status-control" disabled={disabled}>
      <legend className="visually-hidden">Status of {occurrence.name}</legend>
      {OPTIONS.map((option) => (
        <label key={option.value} className={occurrence.status === option.value ? "is-selected" : undefined}>
          <input
            type="radio"
            name={name}
            value={option.value}
            checked={occurrence.status === option.value}
            onChange={() => onChange(option.value)}
          />
          {option.label}
        </label>
      ))}
    </fieldset>
  );
}
