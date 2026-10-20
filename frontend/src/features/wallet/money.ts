const rupeeFormatter = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });

export function formatPaise(paise: number): string {
  return rupeeFormatter.format(paise / 100);
}

export function rupeesToPaise(rupees: string): number | null {
  // Parsed from the text rather than multiplied as a float, so "19.99" becomes exactly 1999 paise.
  const match = /^(\d+)(?:\.(\d{1,2}))?$/.exec(rupees.trim());
  if (match === null) {
    return null;
  }
  const [, whole = "0", fraction = ""] = match;
  return Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
}
