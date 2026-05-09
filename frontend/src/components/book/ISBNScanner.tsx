/**
 * ISBN barcode scanner using html5-qrcode.
 * Loaded dynamically so it doesn't crash on non-camera browsers.
 *
 * Usage:
 *   <ISBNScanner onDetected={(isbn) => handleISBN(isbn)} />
 *
 * The library is loaded from CDN at runtime to keep the bundle light.
 * If the browser doesn't support camera API, the button is hidden.
 */

import { useEffect, useRef, useState } from "react";

interface Props {
  onDetected: (isbn: string) => void;
}

declare global {
  interface Window {
    Html5Qrcode?: any;
  }
}

const CDN_URL =
  "https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js";

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }
    const s = document.createElement("script");
    s.src = src;
    s.onload = () => resolve();
    s.onerror = reject;
    document.head.appendChild(s);
  });
}

export default function ISBNScanner({ onDetected }: Props) {
  const [supported, setSupported] = useState<boolean | null>(null); // null = checking
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scannerRef = useRef<any>(null);
  const containerId = "isbn-scanner-container";

  // Check camera support
  useEffect(() => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setSupported(false);
    } else {
      setSupported(true);
    }
  }, []);

  const startScan = async () => {
    setError(null);
    try {
      await loadScript(CDN_URL);
      setScanning(true);

      // Small delay for DOM to render the container
      await new Promise((r) => setTimeout(r, 100));

      const Html5Qrcode = window.Html5Qrcode;
      scannerRef.current = new Html5Qrcode(containerId);

      await scannerRef.current.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 150 } },
        (decodedText: string) => {
          // Filter: ISBN-10 or ISBN-13
          const cleaned = decodedText.replace(/-/g, "");
          if (/^\d{10}$|^\d{13}$/.test(cleaned)) {
            stopScan();
            onDetected(cleaned);
          }
        },
        () => {} // ignore frame errors
      );
    } catch (e: any) {
      setError("Không thể truy cập camera. Kiểm tra quyền truy cập.");
      setScanning(false);
    }
  };

  const stopScan = async () => {
    if (scannerRef.current) {
      try {
        await scannerRef.current.stop();
        scannerRef.current.clear();
      } catch {}
      scannerRef.current = null;
    }
    setScanning(false);
  };

  // Cleanup on unmount
  useEffect(() => () => { stopScan(); }, []);

  if (supported === false) return null; // No camera — hide silently
  if (supported === null) return null;  // Still checking

  return (
    <div>
      {!scanning ? (
        <button
          type="button"
          onClick={startScan}
          className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:border-blue-300 hover:text-blue-600 transition-colors"
          style={{ minHeight: 40 }}
        >
          📷 Quét ISBN
        </button>
      ) : (
        <div className="space-y-2">
          <div
            id={containerId}
            className="rounded-xl overflow-hidden border-2 border-blue-400"
            style={{ width: "100%", maxWidth: 340 }}
          />
          <button
            type="button"
            onClick={stopScan}
            className="text-sm text-red-500 hover:text-red-700"
            style={{ minHeight: 36 }}
          >
            Dừng quét
          </button>
        </div>
      )}

      {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
    </div>
  );
}
