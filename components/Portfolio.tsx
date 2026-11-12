"use client";
import { useGProContext } from "./GProContext";
import ImageSlot from "./ImageSlot";
import SectionTitle from "./SectionTitle";
import { COLORS } from "@/data/gpro";

export default function Portfolio() {
  const { active,setActive,categories,filteredWorks,card,border,dark,textMain,textSub,chipStyle,setOpenModal } = useGProContext();
  return <>
{/* PORTOFOLIO */}
      <section id="portofolio" className="gpro-container gpro-section">
        <div data-reveal className="gpro-reveal">
          <SectionTitle title="Portofolio" desc="Rangkaian kajian dan karya strategis berdasarkan bidang fokus." />

          <div className="flex snap-x gap-2 overflow-x-auto pb-3">
            {categories.map((c) => {
              const activeBtn = active === c;
              return (
                <button
                  key={c}
                  onClick={() => setActive(c)}
                  aria-pressed={activeBtn} className="min-h-11 shrink-0 snap-start rounded-full border px-4 py-2 text-sm font-semibold transition hover:shadow-sm"
                  style={{
                    borderColor: activeBtn ? COLORS.red : border,
                    backgroundColor: activeBtn ? COLORS.red : card,
                    color: activeBtn ? "#fff" : textSub,
                  }}
                >
                  {c}
                </button>
              );
            })}
          </div>

          <div className="mt-6 grid gap-6 lg:gap-8 md:grid-cols-2 xl:grid-cols-3">
            {filteredWorks.map((w) => (
              <div key={w.title} className="gpro-card flex h-full flex-col rounded-3xl p-6 lg:p-8" style={{ border: `1px solid ${border}`, backgroundColor: card }}>
                <ImageSlot alt={`Sampul portofolio ${w.title}`} ratio="video" className="mb-5" />
                <div className="flex items-start justify-between gap-3">
                  <p className="text-lg font-bold" style={{ color: textMain }}>{w.title}</p>
                  <span className="shrink-0 rounded-full border px-3 py-1 text-sm" style={{ ...chipStyle, color: textMain }}>
                    {w.tag}
                  </span>
                </div>

                <p className="mt-2 text-base leading-7" style={{ color: textSub }}>{w.summary}</p>

                <div className="mt-4 flex flex-wrap gap-2">
                  {w.outputs.map((o) => (
                    <span
                      key={o}
                      className="rounded-full border px-3 py-1 text-sm"
                      style={{
                        borderColor: border,
                        backgroundColor: dark ? "rgba(255,255,255,0.04)" : "#FAFAFA",
                        color: textSub,
                      }}
                    >
                      {o}
                    </span>
                  ))}
                </div>

                <div className="mt-auto flex items-center justify-between gap-3 pt-6">
                  <span className="text-sm font-semibold" style={{ color: textSub }}>Kategori: {w.category}</span>
                  <button className="gpro-btn gpro-btn-ghost" onClick={() => setOpenModal(true)}>
                    Kolaborasi →
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
  </>;
}
