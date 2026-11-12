import Image from "next/image";

type ImageSlotProps = {
  src?: string | null;
  alt: string;
  ratio?: "video" | "square" | "portrait" | "landscape";
  className?: string;
};

const ratios = {
  video: "aspect-video",
  square: "aspect-square",
  portrait: "aspect-[3/4]",
  landscape: "aspect-[4/3]",
} as const;

export default function ImageSlot({ src, alt, ratio = "video", className = "" }: ImageSlotProps) {
  const styles = `relative overflow-hidden rounded-3xl border border-[var(--gpro-border)] bg-gradient-to-br from-[#7DB4CE]/10 via-transparent to-[#D00705]/5 ${ratios[ratio]} ${className}`;
  if (!src) return <div role="img" aria-label={alt} className={styles} />;
  return <div className={styles}><Image src={src} alt={alt} fill sizes="(max-width: 768px) 100vw, 50vw" className="object-cover" /></div>;
}
