type ButtonProps = {
  label: string;
  onClick?: () => void;
  disabled?: boolean;
};

export default function Button({ label, onClick, disabled }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        backgroundColor: "var(--primary)",
        color: "var(--text-main)",
        border: "none",
        padding: "14px 28px",
        fontSize: "16px",
        fontWeight: 600,
        borderRadius: "8px",
        cursor: "pointer",
      }}
    >
      {label}
    </button>
  );
}
