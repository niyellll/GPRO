"use client";
import { useGProContext } from "./GProContext";
import ImageSlot from "./ImageSlot";
import { BRAND, COLORS } from "@/data/gpro";

export default function Hero() {
  const { dark,card,border,textMain,textSub,waLink,setOpenModal,featured } = useGProContext();
  return <>
{/* HERO */}
      <section className="gpro-container pt-20 lg:pt-28">
        <div data-reveal className="gpro-reveal">
          <div
            className="relative min-h-[78vh] overflow-hidden rounded-3xl p-8 sm:p-12 lg:p-16"
            style={{
              border: `1px solid ${border}`,
              background: dark
                ? `linear-gradient(135deg, ${COLORS.blue}14 0%, ${card} 45%, ${COLORS.red}12 100%)`
                : `linear-gradient(135deg, ${COLORS.blue}22 0%, #ffffff 45%, ${COLORS.red}14 100%)`,
            }}
          >
            <div className="grid items-center gap-8 lg:grid-cols-[1.35fr_1fr] lg:gap-12">
              <div className="max-w-3xl">
                <div
                  className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold"
                  style={{ border: `1px solid ${border}`, backgroundColor: card, color: textSub }}
                >
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: COLORS.red }} />
                  STRATEGI • KEBIJAKAN • DATA • PETA • ROADMAP
                </div>

                <h1 className="mt-5 text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl xl:text-7xl" style={{ color: textMain }}>
                  Membuat isu kompleks jadi keputusan yang jelas dan bisa dieksekusi.
                </h1>

                <p className="mt-4 max-w-2xl" style={{ color: textSub }}>
                  {BRAND.full} menyusun kajian strategis, policy brief, peta analitik, dan roadmap implementasi untuk logistik,
                  rantai pasok, biaya ekonomi, kemiskinan, dan edukasi—dengan bahasa yang mudah dipahami dan keluaran yang siap dipakai.
                </p>

                <div className="mt-8 flex flex-col gap-3 xl:flex-row">
                  <a
                    href="#publikasi"
                    className="gpro-btn gpro-btn-secondary gpro-btn-lg w-full xl:w-auto"
                  >
                    Lihat Publikasi
                  </a>

                  <button
                    onClick={() => setOpenModal(true)}
                    className="gpro-btn gpro-btn-primary gpro-btn-lg w-full xl:w-auto"
                  >
                    Ajukan Kolaborasi
                  </button>

                  <a
                    href={waLink} target="_blank" rel="noopener noreferrer"
                    className="gpro-btn gpro-btn-ghost gpro-btn-lg w-full xl:w-auto"
                  >
                    Chat WhatsApp
                  </a>
                </div>
              </div>

              {/* Featured */}
              <div className="min-w-0">
                <ImageSlot alt="Visual utama kajian strategis GPro" ratio="video" className="mb-5" />
                <div className="gpro-card rounded-3xl p-6 lg:p-8" style={{ border: `1px solid ${border}`, backgroundColor: card }}>
                  <p className="text-sm font-semibold" style={{ color: textSub }}>Karya unggulan</p>
                  <p className="mt-2 text-sm font-bold" style={{ color: textMain }}>{featured.title}</p>
                  <p className="mt-2 text-sm" style={{ color: textSub }}>{featured.summary}</p>

                  <div className="mt-4 flex flex-wrap gap-2">
                    {featured.outputs.map((o) => (
                      <span
                        key={o}
                        className="rounded-full border px-3 py-1 text-sm"
                        style={{ borderColor: COLORS.blue, color: textMain, backgroundColor: `${COLORS.blue}12` }}
                      >
                        {o}
                      </span>
                    ))}
                  </div>

                  <div className="mt-5 flex items-center justify-between">
                    <span className="text-sm font-semibold" style={{ color: textSub }}>{featured.tag}</span>
                    <a href="#portofolio" className="text-sm font-semibold" style={{ color: COLORS.red }}>
                      Lihat semua →
                    </a>
                  </div>
                </div>
              </div>
            </div>

            {/* proof strip */}
            <div className="mt-8 grid gap-6 lg:gap-8 md:grid-cols-4">
              {[
                { t: "Berbasis data", d: "Sumber publik & asumsi transparan." },
                { t: "Output siap pakai", d: "Rapi untuk rapat/advokasi." },
                { t: "Visual kuat", d: "Peta/infografik stakeholder-friendly." },
                { t: "Respon cepat", d: "WhatsApp untuk diskusi awal." },
              ].map((x) => (
                <div key={x.t} className="gpro-card rounded-2xl p-5" style={{ border: `1px solid ${border}`, backgroundColor: card }}>
                  <p className="text-sm font-bold" style={{ color: textMain }}>{x.t}</p>
                  <p className="mt-1 text-sm" style={{ color: textSub }}>{x.d}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
  </>;
}
