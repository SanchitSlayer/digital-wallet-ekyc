import { Html5Qrcode } from "html5-qrcode";
import { useEffect, useRef, useState, type ChangeEvent } from "react";

import { errorMessage } from "../../api/client";
import { ErrorMessage } from "../../components/ErrorMessage";

const CAMERA_ELEMENT_ID = "qr-camera";
const FILE_ELEMENT_ID = "qr-file-reader";

export function QrScanner({ onScan }: { onScan: (qrText: string) => void }) {
  const [error, setError] = useState<string | null>(null);
  const onScanRef = useRef(onScan);
  onScanRef.current = onScan;

  useEffect(() => {
    const scanner = new Html5Qrcode(CAMERA_ELEMENT_ID);
    const started = scanner.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: 240 },
      (decodedText) => onScanRef.current(decodedText),
      () => {},
    );
    started.catch((startError) =>
      setError(`Camera unavailable (${errorMessage(startError)}). Upload a photo of the QR code instead.`),
    );
    // React may unmount while the camera is still starting, so stopping waits for start to finish first.
    return () => {
      started.then(() => scanner.stop(), () => undefined);
    };
  }, []);

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file === undefined) {
      return;
    }
    setError(null);
    try {
      onScan(await new Html5Qrcode(FILE_ELEMENT_ID).scanFile(file, false));
    } catch {
      setError(`No QR code was found in ${file.name}. Use a clear, uncropped image of the payment QR.`);
    }
  }

  return (
    <div className="space-y-4">
      <div id={CAMERA_ELEMENT_ID} className="overflow-hidden rounded-lg bg-slate-900" />
      <div id={FILE_ELEMENT_ID} className="hidden" />
      <ErrorMessage message={error} />
      <label className="block text-sm">
        <span className="mb-1 block font-medium text-slate-700">Or upload an image of the QR code</span>
        <input
          type="file"
          accept="image/*"
          onChange={handleFile}
          className="block w-full text-sm file:mr-4 file:rounded-md file:border-0 file:bg-indigo-50 file:px-4 file:py-2 file:text-indigo-700"
        />
      </label>
    </div>
  );
}
