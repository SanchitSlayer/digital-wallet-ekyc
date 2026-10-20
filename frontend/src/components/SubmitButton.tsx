import type { ButtonHTMLAttributes } from "react";

interface SubmitButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  isLoading: boolean;
  loadingLabel: string;
  variant?: "primary" | "danger";
}

const VARIANT_CLASSES = {
  primary: "bg-indigo-600 hover:bg-indigo-700",
  danger: "bg-red-600 hover:bg-red-700",
};

export function SubmitButton({
  isLoading,
  loadingLabel,
  variant = "primary",
  children,
  disabled,
  type = "submit",
  ...buttonProps
}: SubmitButtonProps) {
  return (
    <button
      type={type}
      disabled={isLoading || disabled}
      className={`rounded-md px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 ${VARIANT_CLASSES[variant]}`}
      {...buttonProps}
    >
      {isLoading ? loadingLabel : children}
    </button>
  );
}
