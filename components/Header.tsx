"use client";
import { useGProContext } from "./GProContext";
import Image from "next/image";
import { BRAND, COLORS } from "@/data/gpro";

export default function Header() {
  const { dark,mobileMenu,setDark,setMobileMenu,setOpenModal,card,border,textMain,textSub } = useGProContext();
  return <>
<a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-lg focus:bg-white focus:p-3 focus:text-black">Langsung ke konten</a>
      {/* HEADER */}
      <header
        className="sticky top-0 z-40 backdrop-blur"
        style={{
          backgroundColor: dark ? "rgba(5,5,7,0.72)" : "rgba(255,255,255,0.84)",
          borderBottom: `1px solid ${border}`,
        }}
        
      >
        <div className="gpro-container flex h-20 items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2 sm:gap-3">
            <div
              className="h-11 w-11 shrink-0 overflow-hidden rounded-2xl sm:h-14 sm:w-14"
              style={{ border: `1px solid ${border}`, backgroundColor: card }}
            >
              <Image src="/logo.png" alt="Logo GPro" width={56} height={56} className="h-full w-full object-contain" priority />
            </div>
            <div className="leading-tight">
              <p className="truncate text-sm font-bold sm:text-base" style={{ color: textMain }}>
                {BRAND.short} <span className="hidden font-medium sm:inline" style={{ color: textSub }}>— {BRAND.full}</span>
              </p>
              <p className="hidden text-sm lg:block" style={{ color: textSub }}>{BRAND.subtitle}</p>
            </div>
          </div>

          <nav className="hidden items-center gap-5 text-base font-medium lg:flex" style={{ color: textSub }}>
            <a className="hover:opacity-80" href="#tentang">Tentang</a>
            <a className="hover:opacity-80" href="#publikasi">Publikasi</a>
            <a className="hover:opacity-80" href="#portofolio">Portofolio</a>
            <a className="hover:opacity-80" href="#layanan">Layanan</a>
            <a className="hover:opacity-80" href="#kontak">Kontak</a>
          </nav>

          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
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
  </>;
}
