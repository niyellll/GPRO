"use client";
import { useGProContext } from "./GProContext";
import ImageSlot from "./ImageSlot";
import SectionTitle from "./SectionTitle";
import { COLORS, publications } from "@/data/gpro";

export default function Publications() {
  const { card,border,textMain,textSub,chipStyle,setOpenModal } = useGProContext();
  return <>
{/* PUBLIKASI */}
      <section id="publikasi" className="gpro-container gpro-section">
        <div data-reveal className="gpro-reveal">
          <SectionTitle
            title="Publikasi & Produk"
            desc="Kajian kebijakan, peta analitik, serta publikasi strategis Global Pro-eksistensi."
          />

          <div className="grid gap-6 lg:gap-8 lg:grid-cols-2 xl:grid-cols-2">
            {publications.map((p) => (
              <div key={p.title} className="gpro-card flex h-full flex-col rounded-3xl p-6 lg:p-8" style={{ border: `1px solid ${border}`, backgroundColor: card }}>
                <ImageSlot alt={`Sampul publikasi ${p.title}`} ratio="video" className="mb-5" />
                <div className="flex items-start justify-between gap-3">
                  <p className="text-lg font-bold" style={{ color: textMain }}>{p.title}</p>
                  <span className="rounded-full border px-3 py-1 text-sm font-semibold" style={{ ...chipStyle, color: textMain }}>
                    {p.type}
                  </span>
                </div>
                <p className="mt-2 text-base leading-7" style={{ color: textSub }}>{p.desc}</p>

                <div className="mt-auto flex flex-wrap gap-3 pt-6">
                  {p.url ? <a href={p.url} target="_blank" rel="noopener noreferrer" className="gpro-btn gpro-btn-primary">Unduh / Lihat</a> : <button className="gpro-btn gpro-btn-primary" onClick={() => setOpenModal(true)}>Minta dokumen</button>}
                  {p.url && <button
                    onClick={() => setOpenModal(true)}
                    className="inline-flex items-center justify-center rounded-xl border px-4 py-2 text-sm font-semibold transition hover:-translate-y-0.5 hover:shadow-sm"
                    style={{ borderColor: COLORS.blue, color: textMain, backgroundColor: card }}
                  >
                    Minta versi lengkap
                  </button>}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
  </>;
}
