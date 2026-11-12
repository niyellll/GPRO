"use client";

import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { BRAND, COLORS, works } from "@/data/gpro";

function useGProSite() {
  // ===== THEME =====
  const [dark, setDark] = useState(false);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [formError, setFormError] = useState("");
  const themeReady = useRef(false);

  useEffect(() => {
    // The inline head script already applied the saved preference before hydration.
    const frame = requestAnimationFrame(() => {
      themeReady.current = true;
      setDark(document.documentElement.classList.contains("dark"));
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    if (!themeReady.current) return;
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

  return { dark, setDark, mobileMenu, setMobileMenu, formError, bg, card, border, textMain, textSub, toast, copyText, openModal, setOpenModal, form, setForm, sendToWhatsApp, waLink, chipStyle, categories, active, setActive, filteredWorks, featured };
}

type SiteContext = ReturnType<typeof useGProSite>;
const Context = createContext<SiteContext | null>(null);

export function GProProvider({ children }: { children: ReactNode }) {
  const value = useGProSite();
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useGProContext() {
  const ctx = useContext(Context);
  if (!ctx) throw new Error("GProProvider is required");
  return ctx;
}
