"use client";
import { useGProContext } from "./GProContext";
import ImageSlot from "./ImageSlot";
import SectionTitle from "./SectionTitle";
import { BRAND, COLORS } from "@/data/gpro";

export default function About() {
  const { dark,card,border,textMain,textSub,waLink,copyText,setOpenModal } = useGProContext();
  return <>
{/* TENTANG */}
      <section id="tentang" className="gpro-container gpro-section">
        <div data-reveal className="gpro-reveal">
          <SectionTitle
            title="Tentang GPro"
            desc="GPro (Global Pro-eksistensi) adalah pusat kajian strategis yang membantu organisasi dan pemangku kepentingan mengubah isu rumit menjadi keputusan yang jelas. Fokus kami bukan sekadar “analisis”, tapi menyusun arah, prioritas, dan langkah eksekusi—dengan bahasa yang mudah dipahami dan output yang siap dipakai."
          />

          <div className="grid gap-6 lg:gap-8 md:grid-cols-3">
            <div className="md:col-span-2 gpro-card rounded-3xl p-6 lg:p-8" style={{ border: `1px solid ${border}`, backgroundColor: card }}>
              <ImageSlot alt="Foto tim kajian GPro" ratio="landscape" className="mb-6 max-h-64" />
              <p className="text-sm font-semibold" style={{ color: textSub }}>
                Apa yang GPro kerjakan
              </p>
              <h3 className="mt-2 text-lg font-bold" style={{ color: textMain }}>
                Dari diagnosis masalah → opsi kebijakan → roadmap eksekusi.
              </h3>
              <p className="mt-3 text-base leading-7" style={{ color: textSub }}>
                Banyak kajian berhenti di “penjelasan masalah”. GPro melangkah lebih jauh: merumuskan pertanyaan yang tepat,
                mengubah data menjadi insight yang bisa dipertanggungjawabkan, lalu menyusun pilihan solusi beserta langkah
                implementasi (aktor, tahapan, risiko, dan mitigasinya). Tujuannya sederhana: supaya keputusan bisa diambil lebih
                cepat, lebih rapi, dan lebih mudah dieksekusi.
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                {["Policy brief", "Peta analitik", "Roadmap", "Infografik", "Toolkit 1 halaman", "Deck presentasi"].map((x) => (
                  <span
                    key={x}
                    className="rounded-full border px-3 py-1 text-sm"
                    style={{ borderColor: COLORS.blue, backgroundColor: `${COLORS.blue}12`, color: textMain }}
                  >
                    {x}
                  </span>
                ))}
              </div>

              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl p-4" style={{ border: `1px solid ${border}`, backgroundColor: dark ? "rgba(255,255,255,0.03)" : "#FAFAFA" }}>
                  <p className="text-sm font-bold" style={{ color: textMain }}>Nilai kerja</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm" style={{ color: textSub }}>
                    <li>Transparan pada asumsi dan sumber</li>
                    <li>Rapi, ringkas, stakeholder-friendly</li>
                    <li>Fokus pada langkah implementasi</li>
                  </ul>
                </div>

                <div className="rounded-2xl p-4" style={{ border: `1px solid ${border}`, backgroundColor: dark ? "rgba(255,255,255,0.03)" : "#FAFAFA" }}>
                  <p className="text-sm font-bold" style={{ color: textMain }}>Untuk siapa</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm" style={{ color: textSub }}>
                    <li>Komunitas / NGO</li>
                    <li>Pemerintah daerah & stakeholder</li>
                    <li>Pelaku usaha & kolaborator</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="gpro-card rounded-3xl p-6 lg:p-8" style={{ border: `1px solid ${border}`, backgroundColor: card }}>
              <p className="text-sm font-bold" style={{ color: textMain }}>Kontak cepat</p>
              <p className="mt-2 text-sm" style={{ color: textSub }}>
                Diskusi awal paling cepat lewat WhatsApp. Email untuk kebutuhan dokumen formal.
              </p>

              <div className="mt-6 space-y-3">
                <a href={waLink} target="_blank" rel="noopener noreferrer" className="gpro-btn gpro-btn-primary w-full">Chat WhatsApp</a>
                <p className="text-center text-sm" style={{color:textSub}}>{BRAND.waPretty}</p>
                <a href={`mailto:${BRAND.email}`} className="gpro-btn gpro-btn-secondary w-full">Kirim Email</a>
                <div className="grid grid-cols-2 gap-3"><button className="gpro-btn gpro-btn-ghost" onClick={()=>copyText(BRAND.waPretty,"Nomor WA disalin!")}>Salin Nomor WA</button><button className="gpro-btn gpro-btn-ghost" onClick={()=>copyText(BRAND.email,"Email disalin!")}>Salin Email</button></div>
                <button className="w-full text-center text-sm font-semibold underline underline-offset-4" style={{color:COLORS.red}} onClick={()=>setOpenModal(true)}>Atau isi form kolaborasi</button>
              </div>
            </div>
          </div>

          <div className="mt-4 grid gap-6 lg:gap-8 md:grid-cols-3">
            {[
              { t: "Fokus kajian", d: "Logistik & rantai pasok, biaya ekonomi, kemiskinan, kesehatan bottleneck perkotaan, serta edukasi." },
              { t: "Gaya komunikasi", d: "Bahasa sederhana, struktur jelas, dan visual yang membantu rapat/advokasi." },
              { t: "Hasil yang diharapkan", d: "Stakeholder memahami isu, punya opsi keputusan, dan punya rute eksekusi yang realistis." },
            ].map((x) => (
              <div key={x.t} className="gpro-card rounded-3xl p-6 lg:p-8" style={{ border: `1px solid ${border}`, backgroundColor: card }}>
                <ImageSlot alt={`Ilustrasi layanan ${x.t}`} ratio="landscape" className="mb-5" />
                <p className="text-lg font-bold" style={{ color: textMain }}>{x.t}</p>
                <p className="mt-2 text-base leading-7" style={{ color: textSub }}>{x.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
  </>;
}
