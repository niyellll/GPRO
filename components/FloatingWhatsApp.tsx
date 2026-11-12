"use client";
import { useGProContext } from "./GProContext";

export default function FloatingWhatsApp() {
  const { waLink } = useGProContext();
  return <>
{/* FLOATING WHATSAPP */}
      <a href={waLink} target="_blank" rel="noopener noreferrer" className="fixed bottom-5 right-5 z-50 flex min-h-12 items-center justify-center gap-2 rounded-full bg-[#168943] px-4 py-3 text-sm font-semibold text-white shadow-lg transition hover:-translate-y-1" style={{bottom:"max(20px, env(safe-area-inset-bottom))"}} aria-label="Chat WhatsApp">
        <svg aria-hidden="true" viewBox="0 0 32 32" width="24" height="24" fill="currentColor"><path d="M16 2a14 14 0 0 0-12 21.1L2 30l7.1-1.9A14 14 0 1 0 16 2Zm0 25.5a11.4 11.4 0 0 1-5.8-1.6l-.4-.2-4.2 1.1 1.1-4.1-.3-.4A11.5 11.5 0 1 1 16 27.5Zm6.3-8.6c-.3-.2-1.8-.9-2.1-1s-.5-.2-.7.2-.8 1-1 1.2-.4.2-.7.1a9.5 9.5 0 0 1-4.7-4.1c-.4-.6.4-.6.9-1.6.1-.2 0-.5 0-.7l-1-2.4c-.3-.7-.5-.6-.7-.6h-.6c-.3 0-.7.1-1 .5s-1.3 1.3-1.3 3.1 1.4 3.6 1.6 3.8 3.2 4.8 5.8 6.4c2.1 1.2 3 1.3 4.1 1.2.7-.1 2.1-.9 2.4-1.8s.3-1.7.2-1.8-.3-.3-.6-.4Z"/></svg>
        <span className="hidden sm:inline">Chat WhatsApp</span>
      </a>
  </>;
}
