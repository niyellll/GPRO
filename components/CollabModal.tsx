"use client";
import { useGProContext } from "./GProContext";
import { COLORS } from "@/data/gpro";

export default function CollabModal() {
  const { openModal,setOpenModal,dark,card,border,textMain,textSub,form,setForm,formError,sendToWhatsApp } = useGProContext();
  return <>
{/* MODAL */}
      {openModal ? (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <button
            className="absolute inset-0"
            onClick={() => setOpenModal(false)}
            style={{ backgroundColor: dark ? "rgba(0,0,0,0.72)" : "rgba(0,0,0,0.55)" }}
            aria-label="Tutup formulir"
          />

          <div role="dialog" aria-modal="true" aria-labelledby="gpro-dialog-title" className="relative max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-3xl p-6 shadow-2xl" style={{ backgroundColor: card, border: `1px solid ${border}` }}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold" style={{ color: textSub }}>Form Kolaborasi</p>
                <h3 id="gpro-dialog-title" className="mt-1 text-xl font-bold" style={{ color: textMain }}>Ajukan Kolaborasi</h3>
              </div>
              <button
                onClick={() => setOpenModal(false)}
                aria-label="Tutup formulir" className="gpro-btn gpro-btn-ghost gpro-icon-btn"
                style={{ border: `1px solid ${border}`, backgroundColor: dark ? "rgba(255,255,255,0.04)" : "#fff", color: textMain }}
              >
                <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 6l12 12M18 6L6 18"/></svg>
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
                  aria-label="Organisasi atau instansi" autoComplete="organization" placeholder="Organisasi / Instansi"
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
                  aria-label="Tenggat waktu" placeholder="Tenggat waktu"
                  className="w-full rounded-2xl px-4 py-3 text-sm outline-none"
                  style={{ border: `1px solid ${border}`, backgroundColor: dark ? "rgba(255,255,255,0.04)" : "#fff", color: textMain }}
                />
              </div>

              <textarea
                value={form.detail}
                onChange={(e) => setForm({ ...form, detail: e.target.value })}
                aria-label="Detail kebutuhan" placeholder="Ceritakan singkat kebutuhan kamu…"
                rows={4}
                className="w-full rounded-2xl px-4 py-3 text-sm outline-none"
                style={{ border: `1px solid ${border}`, backgroundColor: dark ? "rgba(255,255,255,0.04)" : "#fff", color: textMain }}
              />

              {formError && <p role="alert" className="text-sm font-semibold" style={{color:COLORS.red}}>{formError}</p>}
              <div className="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                <button onClick={() => setOpenModal(false)} className="gpro-btn gpro-btn-ghost gpro-btn-lg w-full sm:w-auto">Batal</button>
                <button onClick={sendToWhatsApp} disabled={!form.name.trim() || !form.detail.trim()} className="gpro-btn gpro-btn-primary gpro-btn-lg w-full sm:w-auto">Kirim ke WhatsApp</button>
              </div>
            </div>

          </div>
        </div>
      ) : null}
  </>;
}
