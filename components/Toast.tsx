"use client";
import { useGProContext } from "./GProContext";

export default function Toast() {
  const { toast,dark } = useGProContext();
  return <>
{/* TOAST */}
      {toast ? (
        <div className="fixed bottom-24 left-1/2 z-[70] -translate-x-1/2">
          <div
            className="rounded-full px-4 py-2 text-sm font-semibold shadow-lg"
            style={{
              backgroundColor: dark ? "rgba(255,255,255,0.10)" : "rgba(0,0,0,0.75)",
              color: "#fff",
              border: `1px solid ${dark ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.18)"}`,
            }}
          >
            {toast}
          </div>
        </div>
      ) : null}
  </>;
}
