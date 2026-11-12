"use client";
import { useGProContext } from "./GProContext";
import ImageSlot from "./ImageSlot";

export default function CtaBanner() {
  const { dark,card,border,textMain,textSub,waLink,setOpenModal } = useGProContext();
  return <>
{/* AJAKAN KOLABORASI */}
      <section className="gpro-container pt-14">
        <div data-reveal className="gpro-reveal">
          <div
            className="rounded-3xl p-8"
            style={{
              border: `1px solid ${border}`,
              background: dark
                ? `linear-gradient(135deg, rgba(208,7,5,0.10), rgba(11,11,16,1), rgba(125,180,206,0.10))`
                : `linear-gradient(135deg, rgba(208,7,5,0.12), rgba(255,255,255,1), rgba(125,180,206,0.18))`,
            }}
          >
            <ImageSlot alt="Banner kolaborasi dan kajian strategis" ratio="video" className="mb-8 max-h-64" />
            <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
              <div className="max-w-3xl">
                <p className="text-sm font-semibold" style={{ color: textSub }}>Kolaborasi strategis</p>
                <h3 className="mt-2 text-2xl font-extrabold" style={{ color: textMain }}>
                  Butuh policy brief cepat yang rapi dan siap rapat?
                </h3>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm" style={{ color: textSub }}>
                  <li>Struktur jelas: masalah → opsi → rekomendasi → langkah eksekusi</li>
                  <li>Visual pendukung (peta/infografik) untuk stakeholder</li>
                  <li>Bahasa sederhana, mudah dipahami, siap dipakai</li>
                </ul>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <a
                  href={waLink} target="_blank" rel="noopener noreferrer"
                  className="gpro-btn gpro-btn-primary gpro-btn-lg"
                >
                  Chat WA Sekarang
                </a>
                <button
                  onClick={() => setOpenModal(true)}
                  className="gpro-btn gpro-btn-secondary gpro-btn-lg"
                >
                  Ajukan Kolaborasi
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>
  </>;
}
