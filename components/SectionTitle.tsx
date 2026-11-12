function SectionTitle({ title, desc }: { title: string; desc?: string }) {
return <div className="mb-8 lg:mb-10"><h2 className="text-3xl font-extrabold tracking-tight lg:text-4xl" style={{color:"var(--gpro-text)"}}>{title}</h2>{desc && <p className="mt-3 max-w-4xl text-base leading-7 lg:text-lg" style={{color:"var(--gpro-sub)"}}>{desc}</p>}</div>;
}
