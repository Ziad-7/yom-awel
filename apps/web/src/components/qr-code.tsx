import qrcode from "qrcode-generator";

/** A QR code drawn as one SVG path from the module matrix; no generated markup is injected. */
export function QrCode({ value, label }: { value: string; label: string }) {
  const code = qrcode(0, "M");
  code.addData(value);
  code.make();
  const size = code.getModuleCount();
  let path = "";
  for (let row = 0; row < size; row++)
    for (let col = 0; col < size; col++) if (code.isDark(row, col)) path += `M${col + 4} ${row + 4}h1v1h-1z`;
  return (
    <svg className="qr-code" viewBox={`0 0 ${size + 8} ${size + 8}`} role="img" aria-label={label} shapeRendering="crispEdges">
      <rect width={size + 8} height={size + 8} fill="#fff" />
      <path d={path} fill="#1f3632" />
    </svg>
  );
}
