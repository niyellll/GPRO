"use client";
import { useGProContext } from "./GProContext";
import ImageSlot from "./ImageSlot";
import { BRAND } from "@/data/gpro";

export default function Contact() {
  const { card,border,textMain,textSub,waLink,setOpenModal } = useGProContext();
  return <>
{/* KONTAK */}
      <section id="kontak" className="gpro-container gpro-section">
        <div data-reveal className="gpro-reveal">
          <div className="rounded-3xl p-8 lg:p-12" style={{border:`1px solid ${border}`,backgroundColor:card}}>
            <ImageSlot alt="Banner kolaborasi strategis GPro" ratio="video" className="mb-8 max-h-72" />
            <h2 className="text-3xl font-extrabold lg:text-4xl" style={{color:textMain}}>Ajukan kolaborasi</h2>
            <p className="mt-3 max-w-3xl text-base leading-7" style={{color:textSub}}>Diskusikan kebutuhan kajian, dokumen kebijakan, dan roadmap implementasi bersama GPro.</p>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <button className="gpro-btn gpro-btn-primary gpro-btn-lg" onClick={()=>setOpenModal(true)}>Buka Form Kolaborasi</button>
              <a className="gpro-btn gpro-btn-secondary gpro-btn-lg" href={waLink} target="_blank" rel="noopener noreferrer">Chat WhatsApp</a>
              <a className="gpro-btn gpro-btn-ghost gpro-btn-lg" href={`mailto:${BRAND.email}`}>Kirim Email</a>
            </div>
          </div>
        </div>
      </section>
  </>;
}
