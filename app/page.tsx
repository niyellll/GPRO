"use client";

import { GProProvider, useGProContext } from "@/components/GProContext";
import Header from "@/components/Header";
import Hero from "@/components/Hero";
import ReferenceStrip from "@/components/ReferenceStrip";
import About from "@/components/About";
import Publications from "@/components/Publications";
import CtaBanner from "@/components/CtaBanner";
import Portfolio from "@/components/Portfolio";
import Services from "@/components/Services";
import Contact from "@/components/Contact";
import Footer from "@/components/Footer";
import FloatingWhatsApp from "@/components/FloatingWhatsApp";
import Toast from "@/components/Toast";
import CollabModal from "@/components/CollabModal";

function GProContent() {
  const { bg } = useGProContext();
  return (
    <div className="min-h-screen overflow-x-clip" style={{ backgroundColor: bg }}>
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-70">
        <div className="absolute inset-0 gpro-animated-gradient" />
      </div>
      <Header />
      <main id="main-content">
        <Hero />
        <ReferenceStrip />
        <About />
        <Publications />
        <CtaBanner />
        <Portfolio />
        <Services />
        <Contact />
      </main>
      <Footer />
      <FloatingWhatsApp />
      <Toast />
      <CollabModal />
    </div>
  );
}

export default function Home() {
  return <GProProvider><GProContent /></GProProvider>;
}
