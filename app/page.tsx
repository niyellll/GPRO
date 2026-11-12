"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import type { CSSProperties } from "react";

type WorkItem = {
  title: string;
  category: "Logistik" | "PSN" | "Kesehatan" | "Kemiskinan" | "Trade" | "Edukasi";
  tag: string;
  summary: string;
  outputs: string[];
  featured?: boolean;
};

type Publication = {
  title: string;
  type: "PDF" | "Peta" | "Toolkit" | "Slide";
  desc: string;
  url: string;
};

// ===== BRAND / KONTAK =====
const BRAND = {
  short: "GPro",
  full: "Global Pro-eksistensi",
  subtitle: "Pusat Kajian Strategis • Policy • Data • Peta • Roadmap",
  waPlain: "6285899993742",
  waPretty: "+62 858-9999-3742",
  waUrl: "https://wa.me/6285899993742",
  email: "pksgpro@gmail.com",
};

// ===== WARNA (dari logo) =====
const COLORS = {
  red: "#D00705",
  blue: "#7DB4CE",
  ink: "#493D58",
  soft: "#F8FAFD",
};


// ===== DATA =====
const works: WorkItem[] = [
  {
    title: "Kediri sebagai Hub Logistik 2045",
    category: "Logistik",
    tag: "Logistik • 2045",
    summary:
      "Riset & argumentasi kebijakan untuk transformasi Kediri sebagai hub logistik nasional–global, lengkap dengan roadmap strategi.",
    outputs: ["Policy brief", "Roadmap", "Kerangka rantai pasok"],
    featured: true,
  },
  {
    title: "Bandara Dhoho: konektivitas & dampak ekonomi",
    category: "Logistik",
    tag: "Aviation • Logistics",
    summary:
      "Rancangan konektivitas bandara–transportasi dan simulasi dampak ekonomi (penumpang & kargo) untuk memperkuat posisi kawasan.",
    outputs: ["Proposal teknis", "Simulasi dampak", "Strategi koordinasi"],
  },
  {
    title: "Mengapa biaya logistik tidak turun meski PSN dibangun?",
    category: "PSN",
    tag: "PSN • Ekonomi",
    summary:
      "Membedah akar penyebab biaya logistik tetap tinggi dan menyusun rekomendasi perbaikan yang bisa dieksekusi.",
    outputs: ["Dokumen evaluatif", "Infografik", "Rekomendasi transisi mikro"],
  },
  {
    title: "Bottleneck kawasan industri: macet–polusi–kesehatan",
    category: "Kesehatan",
    tag: "Kota • Kesehatan",
    summary:
      "Pemetaan zona risiko kesehatan dan strategi intervensi berbasis zona untuk menurunkan dampak ISPA & stres akibat kemacetan.",
    outputs: ["Peta risiko", "Memo kebijakan", "Toolkit edukasi 1 halaman"],
  },
  {
    title: "Early-Warning Poverty Framework (BPS & PPP)",
    category: "Kemiskinan",
    tag: "Kemiskinan • Perencanaan",
    summary:
      "Kerangka peringatan dini kemiskinan untuk penajaman program, prioritas wilayah, dan perencanaan kebijakan strategis.",
    outputs: ["Framework indikator", "Skema integrasi", "Rekomendasi implementasi"],
  },
  {
    title: "Risiko ekspor: standar global & transisi hijau",
    category: "Trade",
    tag: "Trade Policy • Risiko",
    summary:
      "Kajian risiko sektor ekspor dan strategi mitigasi dalam konteks perubahan standar global dan dinamika perdagangan.",
    outputs: ["Policy memo", "Peta risiko sektor", "Strategi transisi hijau"],
  },
  {
    title: "Kurikulum berbasis PISA untuk SMK",
    category: "Edukasi",
    tag: "Pendidikan • Kurikulum",
    summary:
      "Pengembangan kurikulum literasi–numerasi–sains terapan untuk siswa SMK, dengan struktur yang mudah diterapkan.",
    outputs: ["Outline kurikulum", "Modul ringkas", "Toolkit pembelajaran"],
  },
];

const publications: Publication[] = [
  {
    title: "Policy Brief — Hub Logistik Kediri 2045",
    type: "PDF",
    desc: "Ringkasan kebijakan + roadmap strategi.",
    url: "",
  },
  {
    title: "Peta Analitik — Bottleneck Kawasan Industri",
    type: "Peta",
    desc: "Visual zona risiko & intervensi.",
    url: "",
  },
  {
    title: "Toolkit — Edukasi ISPA & Stres Kemacetan (1 halaman)",
    type: "Toolkit",
    desc: "Materi edukasi publik ringkas.",
    url: "",
  },
  {
    title: "Deck — Evaluasi PSN & Biaya Logistik",
    type: "Slide",
    desc: "Materi presentasi stakeholder.",
    url: "",
  },
];


function SectionTitle({ title, desc }: { title: string; desc?: string }) {
return <div className="mb-8 lg:mb-10"><h2 className="text-3xl font-extrabold tracking-tight lg:text-4xl" style={{color:"var(--gpro-text)"}}>{title}</h2>{desc && <p className="mt-3 max-w-4xl text-base leading-7 lg:text-lg" style={{color:"var(--gpro-sub)"}}>{desc}</p>}</div>;
}
export default function Home() {
  // ===== THEME =====
  const [dark, setDark] = useState(false);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [formError, setFormError] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem("gpro-theme");
    if (saved === "dark") setDark(true);
    else if (saved === "light") setDark(false);
    else {
      const prefers = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
      setDark(Boolean(prefers));
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("gpro-theme", dark ? "dark" : "light");
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  // ===== UI COLORS =====
  const bg = dark ? "#050507" : COLORS.soft;
  const card = dark ? "#0B0B10" : "#FFFFFF";
  const border = dark ? "rgba(255,255,255,0.10)" : "rgba(0,0,0,0.10)";
  const textMain = dark ? "#F4F4F5" : COLORS.ink;
  // FIX light-mode text supaya tidak pucat
  const textSub = dark ? "rgba(244,244,245,0.78)" : "rgba(16,16,24,0.78)";

  // ===== TOAST (Copied!) =====
  const [toast, setToast] = useState<string | null>(null);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 1700);
    return () => clearTimeout(t);
  }, [toast]);

  const copyText = async (txt: string, label = "Copied!") => {
    try {
      await navigator.clipboard.writeText(txt);
      setToast(label);
    } catch {
      // fallback
      const ta = document.createElement("textarea");
      ta.value = txt;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setToast(label);
    }
  };

  // ===== MODAL FORM =====
  const [openModal, setOpenModal] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpenModal(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const [form, setForm] = useState({
    name: "",
    org: "",
    need: "Policy brief",
    deadline: "",
    detail: "",
  });

  const sendToWhatsApp = () => {
    if (!form.name.trim() || !form.detail.trim()) {setFormError("Isi nama dan jelaskan kebutuhan terlebih dahulu.");return;}
    setFormError("");
    const msg = ["Halo GPro, saya ingin kolaborasi.", "", "Nama: "+form.name.trim(), "Organisasi: "+(form.org||"-"), "Kebutuhan: "+form.need, "Deadline: "+(form.deadline||"-"), "Detail: "+form.detail.trim()].join("\n");
    window.open(BRAND.waUrl+"?text="+encodeURIComponent(msg), "_blank", "noopener,noreferrer");
    setOpenModal(false);
  };
  const waLink = BRAND.waUrl + "?text=" + encodeURIComponent("Halo GPro, saya ingin berdiskusi tentang kolaborasi.");
  useEffect(() => {
    if (!openModal) return;
    const prev=document.body.style.overflow; document.body.style.overflow="hidden";
    document.getElementById("gpro-form-name")?.focus();
    const trap=(e:KeyboardEvent)=>{ if(e.key!=="Tab")return; const nodes=document.querySelectorAll<HTMLElement>('[role="dialog"] button:not([disabled]), [role="dialog"] input:not([disabled]), [role="dialog"] select:not([disabled]), [role="dialog"] textarea:not([disabled])');if(!nodes.length)return;const a=nodes[0],b=nodes[nodes.length-1]; if(e.shiftKey&&document.activeElement===a){e.preventDefault();b.focus();}else if(!e.shiftKey&&document.activeElement===b){e.preventDefault();a.focus();}};
    window.addEventListener("keydown",trap);
    return ()=>{document.body.style.overflow=prev;window.removeEventListener("keydown",trap);};
  },[openModal]);
  useEffect(() => {
    if (!openModal) return;
    const prev = document.body.style.overflow;
    const trigger = document.activeElement as HTMLElement | null;
    document.body.style.overflow = "hidden";
    document.getElementById("gpro-form-name")?.focus();
    const trap=(e:KeyboardEvent)=>{
      if(e.key!=="Tab")return;
      const nodes=document.querySelectorAll<HTMLElement>('[role="dialog"] button:not([disabled]), [role="dialog"] input:not([disabled]), [role="dialog"] select:not([disabled]), [role="dialog"] textarea:not([disabled])');
      if(!nodes.length)return;
      const a=nodes[0],b=nodes[nodes.length-1];
      if(e.shiftKey&&document.activeElement===a){e.preventDefault();b.focus();}
      else if(!e.shiftKey&&document.activeElement===b){e.preventDefault();a.focus();}
    };
    window.addEventListener("keydown",trap);
    return ()=>{document.body.style.overflow=prev;window.removeEventListener("keydown",trap);trigger?.focus();};
  },[openModal]);
  // ===== SCROLL REVEAL (konsisten) =====
  useEffect(() => {
    const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const els = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    document.documentElement.classList.add("js");

    if (reduceMotion) {
      els.forEach((el) => el.classList.add("gpro-reveal-in"));
      return;
    }

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (!e.isIntersecting) return;
          (e.target as HTMLElement).classList.add("gpro-reveal-in");
          io.unobserve(e.target);
        });
      },
      { threshold: 0.15 }
    );

    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  const chipStyle: CSSProperties = {
    borderColor: COLORS.blue,
    backgroundColor: `${COLORS.blue}12`,
  };

  const categories = ["Semua", "Logistik", "PSN", "Kesehatan", "Kemiskinan", "Trade", "Edukasi"] as const;
  const [active, setActive] = useState<(typeof categories)[number]>("Semua");

  const filteredWorks = useMemo(() => {
    if (active === "Semua") return works;
    return works.filter((w) => w.category === active);
  }, [active]);

  const featured = works.find((w) => w.featured) ?? works[0];

  return (
    <div className="min-h-screen" style={{ backgroundColor: bg }}>


      {/* BACKGROUND SUBTLE MOVING GRADIENT */}
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-70">
        <div className="absolute inset-0 gpro-animated-gradient" />
      </div>

      {/* HEADER */}
      <header
        className="sticky top-0 z-40 backdrop-blur"
        style={{
          backgroundColor: dark ? "rgba(5,5,7,0.72)" : "rgba(255,255,255,0.84)",
          borderBottom: `1px solid ${border}`,
        }}
        
      >
        <div className="gpro-container flex h-20 items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              className="h-14 w-14 shrink-0 overflow-hidden rounded-2xl"
              style={{ border: `1px solid ${border}`, backgroundColor: card }}
            >
              {/* kalau belum ada logo.png, aman: dia akan hide otomatis */}
              <Image src="/logo.png" alt="Logo GPro" width={56} height={56} className="h-full w-full object-contain" priority />
            </div>
            <div className="leading-tight">
              <p className="text-sm font-bold" style={{ color: textMain }}>
                {BRAND.short} <span className="font-medium" style={{ color: textSub }}>— {BRAND.full}</span>
              </p>
              <p className="text-sm" style={{ color: textSub }}>{BRAND.subtitle}</p>
            </div>
          </div>

          <nav className="hidden items-center gap-5 text-base font-medium lg:flex" style={{ color: textSub }}>
            <a className="hover:opacity-80" href="#tentang">Tentang</a>
            <a className="hover:opacity-80" href="#publikasi">Publikasi</a>
            <a className="hover:opacity-80" href="#portofolio">Portofolio</a>
            <a className="hover:opacity-80" href="#layanan">Layanan</a>
            <a className="hover:opacity-80" href="#kontak">Kontak</a>
          </nav>

          <div className="flex items-center gap-3">
            <button onClick={() => setDark(v=>!v)} className="gpro-btn gpro-btn-ghost gpro-icon-btn" aria-label="Ubah tema"><svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">{dark ? <><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M4.9 19.1l1.4-1.4m11.4-11.4 1.4-1.4"/></> : <path d="M20.985 12.486a9 9 0 1 1-9.47-9.47 7 7 0 0 0 9.47 9.47Z"/>}</svg></button>
            <button onClick={()=>setMobileMenu(v=>!v)} className="gpro-btn gpro-btn-ghost gpro-icon-btn lg:hidden" aria-label={mobileMenu?"Tutup menu":"Buka menu"} aria-expanded={mobileMenu} aria-controls="gpro-mobile-nav"><svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d={mobileMenu?"M6 6l12 12M18 6L6 18":"M4 6h16M4 12h16M4 18h16"}/></svg></button>
            <button
              onClick={() => setOpenModal(true)}
              className="gpro-btn gpro-btn-primary hidden sm:inline-flex"
              style={{ backgroundColor: COLORS.red }}
            >
              Ajukan Kolaborasi
            </button>
          </div>
        </div>
        {mobileMenu && <nav id="gpro-mobile-nav" className="gpro-container flex flex-col gap-1 border-t py-4 lg:hidden" style={{backgroundColor:card,borderColor:border}}>{([["Tentang","#tentang"],["Publikasi","#publikasi"],["Portofolio","#portofolio"],["Layanan","#layanan"],["Kontak","#kontak"]] as const).map(([label,href])=><a key={href} href={href} className="rounded-xl px-4 py-3 font-semibold" onClick={()=>setMobileMenu(false)} style={{color:textMain}}>{label}</a>)}<button className="gpro-btn gpro-btn-primary" onClick={()=>{setMobileMenu(false);setOpenModal(true)}}>Ajukan Kolaborasi</button></nav>}
      </header>

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
                    style={{ backgroundColor: COLORS.red }}
                  >
                    Lihat Publikasi
                  </a>

                  <button
                    onClick={() => setOpenModal(true)}
                    className="gpro-btn gpro-btn-primary gpro-btn-lg w-full xl:w-auto"
                    style={{ borderColor: COLORS.blue, color: textMain, backgroundColor: card }}
                  >
                    Ajukan Kolaborasi
                  </button>

                  <a
                    href={waLink} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center justify-center rounded-xl border px-5 py-3 text-sm font-semibold transition hover:-translate-y-0.5 hover:shadow-sm"
                    style={{ borderColor: border, color: textMain, backgroundColor: card }}
                  >
                    Chat WhatsApp
                  </a>
                </div>
              </div>

              {/* Featured */}
              <div className="min-w-0">
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


      {/* TENTANG */}
      <section id="tentang" className="gpro-container gpro-section">
        <div data-reveal className="gpro-reveal">
          <SectionTitle
            title="Tentang GPro"
            desc="GPro (Global Pro-eksistensi) adalah pusat kajian strategis yang membantu organisasi dan pemangku kepentingan mengubah isu rumit menjadi keputusan yang jelas. Fokus kami bukan sekadar “analisis”, tapi menyusun arah, prioritas, dan langkah eksekusi—dengan bahasa yang mudah dipahami dan output yang siap dipakai."
          />

          <div className="grid gap-6 lg:gap-8 md:grid-cols-3">
            <div className="md:col-span-2 gpro-card rounded-3xl p-6 lg:p-8" style={{ border: `1px solid ${border}`, backgroundColor: card }}>
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
              <div className="mt-5 rounded-2xl p-4" style={{ backgroundColor: `${COLORS.blue}${dark ? "10" : "14"}` }}>
                <p className="text-sm font-semibold" style={{ color: textMain }}>Cara kolaborasi (singkat)</p>
                <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm" style={{ color: textSub }}>
                  <li>Diskusi kebutuhan (WA)</li>
                  <li>Ruang lingkup & output disepakati</li>
                  <li>Draft → review → final</li>
                </ol>
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
                <p className="text-sm font-bold" style={{ color: textMain }}>{x.t}</p>
                <p className="mt-2 text-base leading-7" style={{ color: textSub }}>{x.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* PUBLIKASI */}
      <section id="publikasi" className="gpro-container gpro-section">
        <div data-reveal className="gpro-reveal">
          <SectionTitle
            title="Publikasi & Produk"
            desc="Dokumen dan produk kajian GPro. Materi yang belum tersedia publik dapat diminta melalui form."
          />

          <div className="grid gap-6 lg:gap-8 md:grid-cols-2">
            {publications.map((p) => (
              <div key={p.title} className="gpro-card flex h-full flex-col rounded-3xl p-6 lg:p-8" style={{ border: `1px solid ${border}`, backgroundColor: card }}>
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-bold" style={{ color: textMain }}>{p.title}</p>
                  <span className="rounded-full border px-3 py-1 text-sm font-semibold" style={{ ...chipStyle, color: textMain }}>
                    {p.type}
                  </span>
                </div>
                <p className="mt-2 text-sm" style={{ color: textSub }}>{p.desc}</p>

                <div className="mt-auto flex flex-wrap gap-3 pt-6">
                  {p.url ? <a href={p.url} target="_blank" rel="noopener noreferrer" className="gpro-btn gpro-btn-primary">Unduh / Lihat</a> : <button className="gpro-btn gpro-btn-primary" onClick={() => setOpenModal(true)}>Minta dokumen</button>}
                  <button
                    onClick={() => setOpenModal(true)}
                    className="inline-flex items-center justify-center rounded-xl border px-4 py-2 text-sm font-semibold transition hover:-translate-y-0.5 hover:shadow-sm"
                    style={{ borderColor: COLORS.blue, color: textMain, backgroundColor: card }}
                  >
                    Minta versi lengkap
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

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
                  className="gpro-shine inline-flex items-center justify-center rounded-xl px-6 py-3 text-sm font-semibold text-white transition hover:opacity-90"
                  style={{ backgroundColor: COLORS.red }}
                >
                  Chat WA Sekarang
                </a>
                <button
                  onClick={() => setOpenModal(true)}
                  className="inline-flex items-center justify-center rounded-xl border px-6 py-3 text-sm font-semibold transition hover:-translate-y-0.5 hover:shadow-sm"
                  style={{ borderColor: COLORS.blue, color: textMain, backgroundColor: card }}
                >
                  Ajukan Kolaborasi
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* PORTOFOLIO */}
      <section id="portofolio" className="gpro-container gpro-section">
        <div data-reveal className="gpro-reveal">
          <SectionTitle title="Portofolio" desc="Pilih kategori untuk melihat karya yang relevan." />

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

          <div className="mt-6 grid gap-6 lg:gap-8 md:grid-cols-2">
            {filteredWorks.map((w) => (
              <div key={w.title} className="gpro-card flex h-full flex-col rounded-3xl p-6 lg:p-8" style={{ border: `1px solid ${border}`, backgroundColor: card }}>
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-bold" style={{ color: textMain }}>{w.title}</p>
                  <span className="shrink-0 rounded-full border px-3 py-1 text-sm" style={{ ...chipStyle, color: textMain }}>
                    {w.tag}
                  </span>
                </div>

                <p className="mt-2 text-sm" style={{ color: textSub }}>{w.summary}</p>

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

      {/* LAYANAN */}
      <section id="layanan" className="gpro-container gpro-section">
        <div data-reveal className="gpro-reveal">
          <SectionTitle title="Layanan" desc="Format output yang biasa disiapkan untuk stakeholder dan kolaborator." />

          <div className="grid gap-6 lg:gap-8 md:grid-cols-2">
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

      {/* KONTAK */}
      <section id="kontak" className="gpro-container gpro-section">
        <div data-reveal className="gpro-reveal">
          <div className="rounded-3xl p-8 lg:p-12" style={{border:`1px solid ${border}`,backgroundColor:card}}>
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
      <footer className="gpro-container pb-28 pt-16" style={{color:textSub}}>
        <div className="grid gap-8 border-t pt-8 md:grid-cols-3" style={{borderColor:border}}>
          <div><p className="text-xl font-bold" style={{color:textMain}}>{BRAND.full}</p><p className="mt-2 text-base leading-7">Pusat kajian strategis berbasis data untuk kebijakan yang dapat dilaksanakan.</p></div>
          <div><p className="font-bold" style={{color:textMain}}>Navigasi</p><nav className="mt-3 flex flex-col gap-2">{([["Tentang","#tentang"],["Publikasi","#publikasi"],["Portofolio","#portofolio"],["Layanan","#layanan"],["Kontak","#kontak"]] as const).map(([label,href])=><a key={href} href={href} className="hover:underline">{label}</a>)}</nav></div>
          <div><p className="font-bold" style={{color:textMain}}>Kontak</p><a className="mt-3 block hover:underline" href={waLink} target="_blank" rel="noopener noreferrer">{BRAND.waPretty}</a><a className="mt-2 block hover:underline" href={`mailto:${BRAND.email}`}>{BRAND.email}</a></div>
        </div>
        <p className="mt-10 border-t pt-6 text-sm" style={{borderColor:border}}>© {new Date().getFullYear()} {BRAND.full}. Hak cipta dilindungi.</p>
      </footer>

      {/* FLOATING WHATSAPP */}
      <a href={waLink} target="_blank" rel="noopener noreferrer" className="fixed bottom-5 right-5 z-50 flex min-h-12 items-center justify-center gap-2 rounded-full bg-[#168943] px-4 py-3 text-sm font-semibold text-white shadow-lg transition hover:-translate-y-1" style={{bottom:"max(20px, env(safe-area-inset-bottom))"}} aria-label="Chat WhatsApp">
        <svg aria-hidden="true" viewBox="0 0 32 32" width="24" height="24" fill="currentColor"><path d="M16 2a14 14 0 0 0-12 21.1L2 30l7.1-1.9A14 14 0 1 0 16 2Zm0 25.5a11.4 11.4 0 0 1-5.8-1.6l-.4-.2-4.2 1.1 1.1-4.1-.3-.4A11.5 11.5 0 1 1 16 27.5Zm6.3-8.6c-.3-.2-1.8-.9-2.1-1s-.5-.2-.7.2-.8 1-1 1.2-.4.2-.7.1a9.5 9.5 0 0 1-4.7-4.1c-.4-.6.4-.6.9-1.6.1-.2 0-.5 0-.7l-1-2.4c-.3-.7-.5-.6-.7-.6h-.6c-.3 0-.7.1-1 .5s-1.3 1.3-1.3 3.1 1.4 3.6 1.6 3.8 3.2 4.8 5.8 6.4c2.1 1.2 3 1.3 4.1 1.2.7-.1 2.1-.9 2.4-1.8s.3-1.7.2-1.8-.3-.3-.6-.4Z"/></svg>
        <span className="hidden sm:inline">Chat WhatsApp</span>
      </a>

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

      {/* MODAL */}
      {openModal ? (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <button
            className="absolute inset-0"
            onClick={() => setOpenModal(false)}
            style={{ backgroundColor: dark ? "rgba(0,0,0,0.72)" : "rgba(0,0,0,0.55)" }}
            aria-label="Close modal"
          />

          <div role="dialog" aria-modal="true" aria-labelledby="gpro-dialog-title" className="relative max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-3xl p-6 shadow-2xl" style={{ backgroundColor: card, border: `1px solid ${border}` }}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold" style={{ color: textSub }}>Form Kolaborasi</p>
                <h3 id="gpro-dialog-title" className="mt-1 text-xl font-bold" style={{ color: textMain }}>Ajukan Kolaborasi</h3>
                <p className="mt-2 text-sm" style={{ color: textSub }}>
                  Isi singkat saja. Setelah itu klik <b>Kirim ke WhatsApp</b>.
                </p>
              </div>
              <button
                onClick={() => setOpenModal(false)}
                aria-label="Tutup formulir" className="gpro-btn gpro-btn-ghost gpro-icon-btn"
                style={{ border: `1px solid ${border}`, backgroundColor: dark ? "rgba(255,255,255,0.04)" : "#fff", color: textMain }}
              >
                ✕
              </button>
            </div>

            <div className="mt-5 grid gap-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  id="gpro-form-name" aria-label="Nama" autoComplete="name" placeholder="Nama"
                  className="w-full rounded-2xl px-4 py-3 text-sm outline-none"
                  style={{ border: `1px solid ${border}`, backgroundColor: dark ? "rgba(255,255,255,0.04)" : "#fff", color: textMain }}
                />
                <input
                  value={form.org}
                  onChange={(e) => setForm({ ...form, org: e.target.value })}
                  aria-label="Organisasi atau instansi" autoComplete="organization" aria-label="Organisasi atau instansi" autoComplete="organization" placeholder="Organisasi / Instansi"
                  className="w-full rounded-2xl px-4 py-3 text-sm outline-none"
                  style={{ border: `1px solid ${border}`, backgroundColor: dark ? "rgba(255,255,255,0.04)" : "#fff", color: textMain }}
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <select
                  value={form.need}
                  onChange={(e) => setForm({ ...form, need: e.target.value })}
                  className="w-full rounded-2xl px-4 py-3 text-sm outline-none"
                  style={{ border: `1px solid ${border}`, backgroundColor: dark ? "rgba(255,255,255,0.04)" : "#fff", color: textMain }}
                >
                  <option>Policy brief</option>
                  <option>Peta analitik</option>
                  <option>Roadmap</option>
                  <option>Deck presentasi</option>
                  <option>Lainnya</option>
                </select>

                <input
                  value={form.deadline}
                  onChange={(e) => setForm({ ...form, deadline: e.target.value })}
                  aria-label="Tenggat waktu" aria-label="Tenggat waktu" placeholder="Deadline (contoh: 20 Feb / minggu ini)"
                  className="w-full rounded-2xl px-4 py-3 text-sm outline-none"
                  style={{ border: `1px solid ${border}`, backgroundColor: dark ? "rgba(255,255,255,0.04)" : "#fff", color: textMain }}
                />
              </div>

              <textarea
                value={form.detail}
                onChange={(e) => setForm({ ...form, detail: e.target.value })}
                aria-label="Detail kebutuhan" aria-label="Detail kebutuhan" placeholder="Ceritakan singkat kebutuhan kamu…"
                rows={4}
                className="w-full rounded-2xl px-4 py-3 text-sm outline-none"
                style={{ border: `1px solid ${border}`, backgroundColor: dark ? "rgba(255,255,255,0.04)" : "#fff", color: textMain }}
              />

              {formError && <p role="alert" className="text-sm font-semibold" style={{color:COLORS.red}}>{formError}</p>}
              {formError && <p role="alert" className="text-sm font-semibold" style={{color:COLORS.red}}>{formError}</p>}
              <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm" style={{ color: textSub }}>
                  Tips: isi minimal <b>nama</b> + <b>kebutuhan</b> biar cepat diproses.
                </p>

                <div className="flex gap-3">
                  <button
                    onClick={() => setOpenModal(false)}
                    className="rounded-xl px-4 py-2 text-sm font-semibold transition hover:opacity-90"
                    style={{ border: `1px solid ${border}`, backgroundColor: dark ? "rgba(255,255,255,0.04)" : "#fff", color: textMain }}
                  >
                    Batal
                  </button>
                  <button
                    onClick={sendToWhatsApp} disabled={!form.name.trim() || !form.detail.trim()} disabled={!form.name.trim() || !form.detail.trim()}
                    className="gpro-shine rounded-xl px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
                    style={{ backgroundColor: COLORS.red }}
                  >
                    Kirim ke WhatsApp
                  </button>
                </div>
              </div>
            </div>

            <div className="mt-5 rounded-2xl p-4" style={{ backgroundColor: `${COLORS.blue}${dark ? "10" : "14"}` }}>
              <p className="text-sm font-semibold" style={{ color: textMain }}>Catatan:</p>
              <p className="mt-1 text-sm" style={{ color: textSub }}>
                Tutup modal: klik area gelap atau tekan <b>Esc</b>.
              </p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

