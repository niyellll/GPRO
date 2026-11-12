export type WorkItem = {
  title: string;
  category: "Logistik" | "PSN" | "Kesehatan" | "Kemiskinan" | "Trade" | "Edukasi";
  tag: string;
  summary: string;
  outputs: string[];
  featured?: boolean;
};

export type Publication = {
  title: string;
  type: "PDF" | "Peta" | "Toolkit" | "Slide";
  desc: string;
  url: string;
};

// ===== BRAND / KONTAK =====
export const BRAND = {
  short: "GPro",
  full: "Global Pro-eksistensi",
  subtitle: "Pusat Kajian Strategis • Policy • Data • Peta • Roadmap",
  waPlain: "6285899993742",
  waPretty: "+62 858-9999-3742",
  waUrl: "https://wa.me/6285899993742",
  email: "pksgpro@gmail.com",
};

// ===== WARNA (dari logo) =====
export const COLORS = {
  red: "#D00705",
  blue: "#7DB4CE",
  ink: "#493D58",
  soft: "#F8FAFD",
};


// ===== DATA =====
export const works: WorkItem[] = [
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

export const publications: Publication[] = [
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


