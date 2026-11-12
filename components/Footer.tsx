"use client";
import { useGProContext } from "./GProContext";
import { BRAND } from "@/data/gpro";

export default function Footer() {
  const { border,textMain,textSub,waLink } = useGProContext();
  return <>
<footer className="gpro-container pb-28 pt-16" style={{color:textSub}}>
        <div className="grid gap-8 border-t pt-8 md:grid-cols-3" style={{borderColor:border}}>
          <div><p className="text-xl font-bold" style={{color:textMain}}>{BRAND.full}</p><p className="mt-2 text-base leading-7">Pusat kajian strategis berbasis data untuk kebijakan yang dapat dilaksanakan.</p></div>
          <div><p className="font-bold" style={{color:textMain}}>Navigasi</p><nav className="mt-3 flex flex-col gap-2">{([["Tentang","#tentang"],["Publikasi","#publikasi"],["Portofolio","#portofolio"],["Layanan","#layanan"],["Kontak","#kontak"]] as const).map(([label,href])=><a key={href} href={href} className="hover:underline">{label}</a>)}</nav></div>
          <div><p className="font-bold" style={{color:textMain}}>Kontak</p><a className="mt-3 block hover:underline" href={waLink} target="_blank" rel="noopener noreferrer">{BRAND.waPretty}</a><a className="mt-2 block hover:underline" href={`mailto:${BRAND.email}`}>{BRAND.email}</a></div>
        </div>
        <p className="mt-10 border-t pt-6 text-sm" style={{borderColor:border}}>© {new Date().getFullYear()} {BRAND.full}. Hak cipta dilindungi.</p>
      </footer>
  </>;
}
