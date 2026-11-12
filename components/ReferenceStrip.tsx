"use client";
import { useGProContext } from "./GProContext";
import Image from "next/image";

export default function ReferenceStrip() {
  const { dark,card,border,textMain,textSub } = useGProContext();
  return <>
{/* PARTNER / REFERENSI STRIP */}
<section className="gpro-container pt-20 lg:pt-28">
  <div data-reveal className="gpro-reveal">
    <div
      className="rounded-3xl p-6"
      style={{ border: `1px solid ${border}`, backgroundColor: card }}
    >
      <p className="text-sm font-semibold" style={{ color: textMain }}>
        Rujukan data & riset kami
      </p>
      <p className="mt-2 text-base" style={{color:textSub}}>Logo milik masing-masing lembaga. GPro merujuk publikasi publik mereka sebagai sumber riset, bukan pernyataan kemitraan resmi.</p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 md:grid-cols-4">
        {[
          { name: "McKinsey & Company", src: "/mckinsey.png", href: "https://www.mckinsey.com" },
          { name: "World Economic Forum", src: "/wef.png", href: "https://www.weforum.org" },
          { name: "International Labour Organization", src: "/ilo.png", href: "https://www.ilo.org" },
          { name: "The World Bank", src: "/worldbank.png", href: "https://www.worldbank.org" },
        ].map((p) => (
          <a
            key={p.name}
            href={p.href}
            target="_blank"
            rel="noreferrer"
            className="gpro-card flex items-center justify-center rounded-2xl px-4 py-6"
            style={{
              border: `1px solid ${border}`,
              backgroundColor: dark ? "rgba(255,255,255,0.04)" : "#fff",
            }}
            title={p.name}
          >
            <Image src={p.src} alt={p.name} width={160} height={50} className="h-12 w-auto max-w-full object-contain opacity-90 transition hover:opacity-100" />
          </a>
        ))}
      </div>
    </div>
  </div>
</section>
  </>;
}
