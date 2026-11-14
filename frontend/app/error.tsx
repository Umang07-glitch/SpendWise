"use client";
export default function ErrorPage({reset}:{reset:()=>void}){return <main className="mx-auto max-w-lg p-12 text-center"><h1 className="text-2xl font-bold">Something went wrong</h1><p className="mt-4 text-slate-500">Please retry loading your workspace.</p><button onClick={reset} className="mt-6 rounded-xl bg-primary px-5 py-3 text-white">Try again</button></main>;}
