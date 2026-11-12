"use client";
import { useGProContext } from "./GProContext";
import SectionTitle from "./SectionTitle";

export default function Services() {
  const { card,border,textMain,textSub } = useGProContext();
  return <>
{/* LAYANAN */}
      <section id="layanan" className="gpro-container gpro-section">
        <div data-reveal className="gpro-reveal">
          <SectionTitle title="Layanan" desc="Format output yang biasa disiapkan untuk stakeholder dan kolaborator." />

          <div className="grid gap-6 lg:gap-8 md:grid-cols-2 xl:grid-cols-4">
            {[
              { t: "Policy Brief & Memo", d: "Dokumen ringkas, jelas, siap dipakai rapat/advokasi." },
              { t: "Peta Analitik & Visual", d: "Peta/infografik stakeholder-friendly, metodologi transparan." },
              { t: "Roadmap Implementasi", d: "Tahapan kerja, prioritas, timeline, aktor, risiko, langkah eksekusi." },
              { t: "Deck Presentasi", d: "Materi presentasi profesional yang singkat, tajam, rapi." },
            ].map((x) => (
              <div key={x.t} className="gpro-card rounded-3xl p-6 lg:p-8" style={{ border: `1px solid ${border}`, backgroundColor: card }}>
                <p className="text-sm font-bold" style={{ color: textMain }}>{x.t}</p>
                <p className="mt-2 text-base leading-7" style={{ color: textSub }}>{x.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
  </>;
}
