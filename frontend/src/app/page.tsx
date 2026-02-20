"use client";

import { useState, useEffect } from "react";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export default function Home() {
    const [wallets, setWallets] = useState<string[]>([]);
    const [trades, setTrades] = useState<any[]>([]);
    const [newWallet, setNewWallet] = useState("");
    const [isConnected, setIsConnected] = useState(false);
    const [stats, setStats] = useState({ balance: 100.0, initial_balance: 100.0 });
    const [filters, setFilters] = useState<string[]>([]);
    const [newFilter, setNewFilter] = useState("");
    const [availableCategories, setAvailableCategories] = useState<string[]>([]);

    useEffect(() => {
        // Initial fetch
        fetchConfig();
        fetchTrades();
        fetchAvailableCategories();

        const interval = setInterval(() => {
            fetchConfig();
            fetchTrades();
        }, 5000);
        return () => clearInterval(interval);
    }, []);

    const fetchAvailableCategories = async () => {
        try {
            const res = await fetch(`${BACKEND_URL}/available-categories`);
            if (res.ok) {
                const data = await res.json();
                setAvailableCategories(data.categories || []);
            }
        } catch (error) {
            console.error("Failed to fetch available categories", error);
        }
    };

    const fetchConfig = async () => {
        try {
            const res = await fetch(`${BACKEND_URL}/config`);
            if (res.ok) {
                const data = await res.json();
                setWallets(data.tracked_wallets || []);
                if (data.stats) setStats(data.stats);
                if (data.filters) setFilters(data.filters);
                setIsConnected(true);
            } else {
                setIsConnected(false);
            }
        } catch (error) {
            setIsConnected(false);
        }
    };

    const clearTrades = async () => {
        try {
            const res = await fetch(`${BACKEND_URL}/trades/clear`, { method: "POST" });
            if (res.ok) {
                fetchTrades();
                fetchConfig();
            }
        } catch (error) {
            console.error("Failed to clear trades", error);
        }
    };

    const addFilter = async (category?: string) => {
        const catToAdd = category || newFilter;
        if (!catToAdd) return;
        try {
            const res = await fetch(`${BACKEND_URL}/filters/add?category=${catToAdd}`, {
                method: "POST",
            });
            if (res.ok) {
                const data = await res.json();
                setFilters(data.filters);
                if (!category) setNewFilter("");
            }
        } catch (error) {
            console.error("Failed to add filter", error);
        }
    };

    const removeFilter = async (category: string) => {
        try {
            const res = await fetch(`${BACKEND_URL}/filters/remove?category=${category}`, {
                method: "POST",
            });
            if (res.ok) {
                const data = await res.json();
                setFilters(data.filters);
            }
        } catch (error) {
            console.error("Failed to remove filter", error);
        }
    };

    const fetchTrades = async () => {
        try {
            const res = await fetch(`${BACKEND_URL}/trades`);
            if (res.ok) {
                const data = await res.json();
                setTrades(data);
            }
        } catch (error) {
            console.error("Failed to fetch trades", error);
        }
    };

    const addWallet = async () => {
        if (!newWallet) return;
        try {
            const res = await fetch(`${BACKEND_URL}/wallets/add?address=${newWallet}`, {
                method: "POST",
            });
            if (res.ok) {
                const data = await res.json();
                setWallets(data.wallets);
                setNewWallet("");
            }
        } catch (error) {
            console.error("Failed to add wallet", error);
        }
    };

    const removeWallet = async (address: string) => {
        try {
            const res = await fetch(`${BACKEND_URL}/wallets/remove?address=${address}`, {
                method: "POST",
            });
            if (res.ok) {
                const data = await res.json();
                setWallets(data.wallets);
            }
        } catch (error) {
            console.error("Failed to remove wallet", error);
        }
    };

    return (
        <main className="min-h-screen bg-[#020617] text-slate-100 p-8 font-sans selection:bg-blue-500/30">
            <div className="max-w-7xl mx-auto">
                <header className="mb-12 flex justify-between items-center border-b border-slate-800/60 pb-8">
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            <span className="bg-blue-600 text-white text-[10px] font-black px-1.5 py-0.5 rounded leading-none">PRO</span>
                            <h1 className="text-3xl font-bold tracking-tight text-slate-100 italic">
                                ANTIGRAVITY <span className="text-slate-500 font-normal">TERMINAL</span>
                            </h1>
                        </div>
                        <p className="text-slate-500 text-sm font-medium">Precision algorithmic replication for Polymarket</p>
                    </div>
                    <div>
                        <div className="flex items-center gap-3 bg-slate-900/60 border border-slate-800 px-5 py-2.5 rounded-2xl">
                            <div className={`w-2.5 h-2.5 ${isConnected ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.4)]' : 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.4)]'} rounded-full`} />
                            <div>
                                <div className="text-[10px] font-black uppercase tracking-widest text-slate-400">System Status</div>
                                <div className="text-[11px] font-bold text-slate-200">{isConnected ? 'ONLINE & TRACKING' : 'OFFLINE / DISCONNECTED'}</div>
                            </div>
                        </div>
                    </div>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Left Column: Config & Stats */}
                    <div className="space-y-8">
                        {/* Monitor Section */}
                        <section className="bg-slate-900/50 border border-slate-800/60 p-7 rounded-3xl">
                            <div className="flex items-center gap-3 mb-6">
                                <div className="p-2 bg-blue-500/10 rounded-lg text-blue-500">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
                                </div>
                                <h2 className="text-xs font-black uppercase tracking-[0.2em] text-slate-300">Wallet Observers</h2>
                            </div>

                            <div className="space-y-5">
                                <form onSubmit={(e) => { e.preventDefault(); addWallet(); }} className="relative group">
                                    <input
                                        value={newWallet}
                                        onChange={(e) => setNewWallet(e.target.value)}
                                        placeholder="Add target explorer address (0x...)"
                                        className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-4 pr-20 py-3 text-sm focus:outline-none focus:border-blue-500/50 transition-all placeholder:text-slate-700 text-slate-200"
                                    />
                                    <button type="submit" className="absolute right-2 top-1.5 bottom-1.5 px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-all font-black text-[10px] tracking-widest active:scale-95">
                                        OBSERVE
                                    </button>
                                </form>

                                <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                                    {wallets.length === 0 ? (
                                        <div className="flex flex-col items-center justify-center py-10 border border-dashed border-slate-800/60 rounded-2xl bg-slate-950/20">
                                            <p className="text-slate-600 text-[10px] uppercase font-black tracking-widest">No Active Monitored Target</p>
                                            <p className="text-slate-700 text-[9px] mt-1">Enter a Polymarket wallet to start</p>
                                        </div>
                                    ) : (
                                        wallets.map((addr) => (
                                            <div key={addr} className="flex items-center justify-between bg-slate-950 border border-slate-800/40 p-3 rounded-xl group hover:border-blue-500/30 transition-all">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                                                    <span className="text-xs font-mono text-slate-400 group-hover:text-slate-200 transition-colors uppercase">{addr.slice(0, 10)}...{addr.slice(-6)}</span>
                                                </div>
                                                <button onClick={() => removeWallet(addr)} className="opacity-0 group-hover:opacity-100 text-slate-700 hover:text-red-500 transition-all p-1">
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
                                                </button>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        </section>

                        {/* Filters Section */}
                        <section className="bg-slate-900/50 border border-slate-800/60 p-7 rounded-3xl">
                            <div className="flex items-center gap-3 mb-6">
                                <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-500">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" /></svg>
                                </div>
                                <h2 className="text-xs font-black uppercase tracking-[0.2em] text-slate-300">Strategy Filters</h2>
                            </div>

                            <div className="space-y-6">
                                <div className="space-y-3">
                                    <div className="text-[10px] text-slate-600 uppercase font-black tracking-widest pl-1">Suggested Keywords</div>
                                    <div className="relative group">
                                        <select
                                            onChange={(e) => { if (e.target.value) { addFilter(e.target.value); e.target.value = ""; } }}
                                            className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-3 text-xs font-bold focus:outline-none focus:border-indigo-500/50 transition-all text-slate-400 appearance-none cursor-pointer"
                                        >
                                            <option value="" disabled selected>Explore market tags...</option>
                                            {availableCategories.filter(cat => !filters.includes(cat.toLowerCase())).map(cat => (
                                                <option key={cat} value={cat}>{cat}</option>
                                            ))}
                                        </select>
                                        <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-600 group-hover:text-indigo-400 transition-colors">
                                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="m6 9 6 6 6-6" /></svg>
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    <div className="text-[10px] text-slate-600 uppercase font-black tracking-widest pl-1 text-right">Manual Input</div>
                                    <div className="flex gap-2 relative">
                                        <input
                                            value={newFilter}
                                            onChange={(e) => setNewFilter(e.target.value)}
                                            placeholder="Add custom niche..."
                                            className="flex-1 bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-3 text-xs focus:outline-none focus:border-indigo-500/50 transition-all placeholder:text-slate-700 font-mono text-slate-300"
                                        />
                                        <button onClick={() => addFilter()} className="px-5 bg-slate-800 hover:bg-indigo-600 hover:text-white text-slate-400 rounded-xl transition-all font-black text-[10px] tracking-widest active:scale-95 uppercase">
                                            Apply
                                        </button>
                                    </div>
                                </div>

                                <div className="pt-4 border-t border-slate-800/40">
                                    <div className="flex flex-wrap gap-2 min-h-[40px] items-center">
                                        {filters.length === 0 ? (
                                            <div className="w-full bg-slate-950/40 border border-dashed border-slate-800/60 p-3 rounded-xl text-center">
                                                <p className="text-slate-600 text-[9px] uppercase font-black tracking-widest leading-relaxed">System Wide Monitoring Active<br /><span className="text-slate-700 font-normal mt-0.5 block">(No Filters Engaged)</span></p>
                                            </div>
                                        ) : (
                                            filters.map((cat) => (
                                                <div key={cat} className="flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 px-3 py-1.5 rounded-lg hover:border-indigo-500/40 transition-colors cursor-default">
                                                    <span className="text-[10px] font-black text-indigo-400 uppercase tracking-widest">{cat}</span>
                                                    <button onClick={() => removeFilter(cat)} className="text-slate-600 hover:text-red-400 transition-all">
                                                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="4"><path d="M18 6 6 18M6 6l12 12" /></svg>
                                                    </button>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Portfolio Section */}
                        <section className="bg-slate-900/30 border border-slate-800/40 p-7 rounded-3xl">
                            <div className="flex items-center gap-3 mb-6">
                                <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-500">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></svg>
                                </div>
                                <h2 className="text-xs font-black uppercase tracking-[0.2em] text-slate-300">Shadow Account</h2>
                            </div>

                            <div className="space-y-6">
                                <div>
                                    <div className="flex justify-between items-center mb-1 pr-1">
                                        <div className="text-[10px] text-slate-600 uppercase font-black tracking-widest flex items-center gap-1 group">
                                            Simulation Balance
                                            <span className="cursor-help opacity-50 text-[12px]">ⓘ</span>
                                        </div>
                                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-tighter">Live Paper-Trading</span>
                                    </div>
                                    <div className="text-3xl font-bold text-slate-100 tabular-nums tracking-tight">
                                        <span className="text-emerald-500/60 text-xl mr-1 font-mono">$</span>
                                        {stats.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-slate-950/40 p-4 rounded-2xl border border-slate-800/40 group hover:border-emerald-500/20 transition-all">
                                        <div className="text-[9px] text-slate-600 uppercase font-black mb-1.5 tracking-tighter">Net Yield (PnL)</div>
                                        <div className={`text-sm font-black tabular-nums tracking-widest ${(stats.balance - stats.initial_balance) >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                                            {(stats.balance - stats.initial_balance) >= 0 ? '+' : ''}
                                            {((stats.balance - stats.initial_balance)).toFixed(2)}
                                        </div>
                                    </div>
                                    <div className="bg-slate-950/40 p-4 rounded-2xl border border-slate-800/40 group hover:border-slate-700 transition-all">
                                        <div className="text-[9px] text-slate-600 uppercase font-black mb-1.5 tracking-tighter">Starting Cap</div>
                                        <div className="text-sm font-black text-slate-500 tabular-nums tracking-widest">${stats.initial_balance}</div>
                                    </div>
                                </div>
                            </div>
                        </section>
                    </div>

                    {/* Right Column: Replication Engine */}
                    <div className="lg:col-span-2 space-y-10">
                        <section className="bg-slate-900/60 border border-slate-800/60 rounded-3xl flex flex-col h-full min-h-[700px] overflow-hidden shadow-2xl">
                            <div className="px-8 py-5 border-b border-slate-800/60 flex justify-between items-center bg-slate-900/20">
                                <div className="flex items-center gap-3">
                                    <div className="p-1.5 bg-slate-800 rounded-md">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>
                                    </div>
                                    <h2 className="text-xs font-black uppercase tracking-[0.2em] text-slate-200">System Execution Logs</h2>
                                </div>
                                <button
                                    onClick={clearTrades}
                                    className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600 hover:text-red-400 transition-all border border-slate-800/60 px-4 py-2 rounded-xl hover:bg-red-500/5 hover:border-red-500/20 font-mono active:scale-95"
                                >
                                    WIPE_FEED
                                </button>
                            </div>
                            <div className="flex-1 p-8 overflow-y-auto space-y-5">
                                {trades.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center h-full text-center opacity-30 select-none pointer-events-none">
                                        <div className="w-16 h-16 border-2 border-dashed border-slate-700 rounded-full flex items-center justify-center mb-6">
                                            <div className="w-2 h-2 bg-slate-700 rounded-full animate-pulse" />
                                        </div>
                                        <p className="text-[11px] tracking-[0.3em] uppercase font-black text-slate-500">Listening for transaction signals...</p>
                                        <p className="text-[9px] text-slate-600 mt-2 font-medium tracking-wide">Syncing with blockchain observers</p>
                                    </div>
                                ) : (
                                    trades.map((trade) => (
                                        <div key={trade.id} className="border border-slate-800/50 p-6 rounded-2xl bg-slate-950/40 hover:bg-slate-950/60 transition-all group">
                                            <div className="flex justify-between items-start mb-4">
                                                <div className="flex flex-wrap items-center gap-3">
                                                    <div className={`px-2.5 py-1 rounded border text-[10px] font-black uppercase tracking-widest ${trade.side === 'BUY' ? 'bg-blue-500/10 border-blue-500/30 text-blue-400' : 'bg-amber-500/10 border-amber-500/30 text-amber-400'}`}>
                                                        {trade.side} EXECUTED
                                                    </div>
                                                    {trade.category && trade.category !== 'All' && (
                                                        <div className="flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1 rounded">
                                                            <div className="w-1 h-1 bg-indigo-500 rounded-full" />
                                                            <span className="text-[10px] font-black text-indigo-300 uppercase tracking-widest">
                                                                {trade.category}
                                                            </span>
                                                        </div>
                                                    )}
                                                </div>
                                                <span className="text-[10px] text-slate-600 font-black font-mono tracking-tighter bg-slate-900/40 px-2 py-1 rounded uppercase">{trade.timestamp} UTC</span>
                                            </div>

                                            <div className="text-sm font-black text-slate-100 mb-6 tracking-normal uppercase border-l-4 border-slate-700 pl-4 py-0.5 leading-relaxed group-hover:border-blue-500/50 transition-all">{trade.market}</div>

                                            <div className="grid grid-cols-4 gap-3">
                                                <div className="bg-slate-900/40 p-3 rounded-xl border border-slate-800/40 group-hover:border-slate-800 transition-all">
                                                    <div className="text-[8px] uppercase text-slate-600 font-black mb-1.5 tracking-widest">Observer</div>
                                                    <div className="text-[10px] text-slate-400 font-mono font-bold">{trade.wallet.slice(0, 8)}...</div>
                                                </div>
                                                <div className="bg-slate-900/40 p-3 rounded-xl border border-slate-800/40 group-hover:border-blue-500/10 transition-all">
                                                    <div className="text-[8px] uppercase text-slate-600 font-black mb-1.5 tracking-widest">Trade Value</div>
                                                    <div className="text-[11px] text-emerald-500 font-black tabular-nums tracking-tighter">${(trade.total_cost || (trade.amount * trade.price)).toFixed(2)}</div>
                                                </div>
                                                <div className="bg-slate-900/40 p-3 rounded-xl border border-slate-800/40 group-hover:border-slate-800 transition-all">
                                                    <div className="text-[8px] uppercase text-slate-600 font-black mb-1.5 tracking-widest">Volume</div>
                                                    <div className="text-[11px] text-slate-300 font-black tabular-nums tracking-widest">{trade.amount.toFixed(1)} <span className="text-[8px] text-slate-600">UNIT</span></div>
                                                </div>
                                                <div className="bg-slate-900/40 p-3 rounded-xl border border-slate-800/40 group-hover:border-blue-500/10 transition-all">
                                                    <div className="text-[8px] uppercase text-slate-600 font-black mb-1.5 tracking-widest">Index Price</div>
                                                    <div className="text-[11px] text-blue-400 font-black tabular-nums tracking-tighter">${trade.price.toFixed(3)}</div>
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </section>
                    </div>
                </div>
            </div>
        </main>
    );
}
