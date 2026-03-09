"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import { motion, Reorder, AnimatePresence } from "framer-motion";
import { Amplify, Auth, Hub } from "aws-amplify";
import { loadStripe } from "@stripe/stripe-js";

// Load config from json (assuming it will be populated)
// In a real build process, these would be env vars
import awsConfig from "../../.aws_config.json";

if (awsConfig.USER_POOL_ID) {
    Amplify.configure({
        Auth: {
            region: awsConfig.REGION,
            userPoolId: awsConfig.USER_POOL_ID,
            userPoolWebClientId: awsConfig.USER_POOL_CLIENT_ID,
            identityPoolId: (awsConfig as any).IDENTITY_POOL_ID,
            oauth: {
                domain: (process.env.NEXT_PUBLIC_COGNITO_DOMAIN || "us-east-1jkqtjhrlo.auth.us-east-1.amazoncognito.com").replace(/^https?:\/\//, ""),
                scope: ["email", "profile", "openid"],
                redirectSignIn: (typeof window !== 'undefined' ? window.location.origin : "http://localhost:3001") + "/",
                redirectSignOut: (typeof window !== 'undefined' ? window.location.origin : "http://localhost:3001") + "/",
                responseType: "code"
            }
        }
    });
} else {
    // Dummy config to prevent Amplify from throwing errors in Local dev
    Amplify.configure({
        Auth: {
            region: "us-east-1",
            userPoolId: "us-east-1_dummy",
            userPoolWebClientId: "dummy",
            mandatorySignIn: false
        }
    });
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// Vision UI High-Fidelity Icons
const Icons = {
    Dashboard: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /></svg>,
    Fleet: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" /></svg>,
    Matrix: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21V5a2 2 0 00-2-2H5a2 2 0 00-2 2v16" /><path d="M21 21V9a2 2 0 00-2-2h-5M3 7h9M3 11h9M3 15h9" /><rect x="11" y="20" width="2" height="2" rx="0.5" /></svg>,
    Strategy: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" /></svg>,
    Search: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>,
    Notifications: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0" /></svg>,
    Messages: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" /></svg>,
    Plus: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>,
    Trash: () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" /></svg>,
    Settings: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.22 2h-.44a2 2 0 00-2 2v.18a2 2 0 01-1 1.73l-.43.25a2 2 0 01-2 0l-.15-.08a2 2 0 00-2.73.73l-.22.38a2 2 0 00.73 2.73l.15.1a2 2 0 011 1.72v.51a2 2 0 01-1 1.74l-.15.09a2 2 0 00-.73 2.73l.22.38a2 2 0 002.73.73l.15-.08a2 2 0 012 0l.43.25a2 2 0 011 1.73V20a2 2 0 002 2h.44a2 2 0 002-2v-.18a2 2 0 011-1.73l.43-.25a2 2 0 012 0l.15.08a2 2 0 002.73-.73l.22-.39a2 2 0 00-.73-2.73l-.15-.08a2 2 0 01-1-1.74v-.5a2 2 0 011-1.74l.15-.09a2 2 0 00.73-2.73l-.22-.38a2 2 0 00-2.73-.73l-.15.08a2 2 0 01-2 0l-.43-.25a2 2 0 01-1-1.73V4a2 2 0 00-2-2z" /><circle cx="12" cy="12" r="3" /></svg>,
    Help: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3M12 17h.01" /></svg>,
    Logout: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" /></svg>,
};

export default function Home() {
    const [wallets, setWallets] = useState<string[]>([]);
    const [trades, setTrades] = useState<any[]>([]);
    const [newWallet, setNewWallet] = useState("");
    const [stats, setStats] = useState({ balance: 100.0, initial_balance: 100.0 });
    const [balanceHistory, setBalanceHistory] = useState<{ timestamp: number; balance: number }[]>([]);
    const [filters, setFilters] = useState<string[]>([]);
    const [newFilter, setNewFilter] = useState("");
    const [availableCategories, setAvailableCategories] = useState<string[]>([]);
    const [selectedWallet, setSelectedWallet] = useState<string | null>(null);
    const [leaderboard, setLeaderboard] = useState<any[]>([]);
    const [whales, setWhales] = useState<any[]>([]);
    const [signals, setSignals] = useState<any[]>([]);
    const [heatmap, setHeatmap] = useState<any[]>([]);
    const [aiPortfolio, setAIPortfolio] = useState<any>(null);
    const [socialFeed, setSocialFeed] = useState<any[]>([]);
    const [activeTab, setActiveTab] = useState<"IDENTITY" | "OVERVIEW" | "FLEET" | "REPLICATION" | "STRATEGY" | "SOCIAL" | "SETTINGS" | "SUBSCRIPTION">("IDENTITY");

    // Feature State
    const [disabledWallets, setDisabledWallets] = useState<string[]>([]);
    const [terminatedWallets, setTerminatedWallets] = useState<string[]>([]);
    const [initialBalanceInput, setInitialBalanceInput] = useState("100.0");
    const [profiles, setProfiles] = useState<Record<string, any>>({});
    const [balanceThreshold, setBalanceThreshold] = useState("0.0");
    const [dailyPnlThreshold, setDailyPnlThreshold] = useState("1000.0");
    const [tradingMode, setTradingMode] = useState<"paper" | "live">("paper");
    const [livePolymarketAddress, setLivePolymarketAddress] = useState("");
    const [userProfile, setUserProfile] = useState<{ name?: string | null; picture?: string | null; email?: string | null }>({ name: null, picture: null, email: null });

    // Auth State
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [user, setUser] = useState<{ username: string; email?: string; picture?: string } | null>(null);
    const [isAuthenticating, setIsAuthenticating] = useState(true);

    // Filter State
    const [searchAddress, setSearchAddress] = useState("");
    const [sideFilter, setSideFilter] = useState<"ALL" | "BUY" | "SELL">("ALL");
    const [dragActive, setDragActive] = useState(false);
    const [allocationWeights, setAllocationWeights] = useState<Record<string, string>>({});
    const lastCapitalResetAt = useRef<number>(0);
    const [isPageVisible, setIsPageVisible] = useState(true);

    const handleUpdateAllocation = (address: string, weight: string) => {
        setAllocationWeights(prev => ({ ...prev, [address]: weight }));
        // In a real implementation, this would also call a backend API
        console.log(`Updated allocation for ${address} to ${weight}%`);
    };

    useEffect(() => {
        const handleVisibilityChange = () => setIsPageVisible(document.visibilityState === "visible");
        document.addEventListener("visibilitychange", handleVisibilityChange);
        return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
    }, []);

    useEffect(() => {
        const checkUser = async () => {
            try {
                if (!awsConfig.USER_POOL_ID) throw new Error("Mock Mode");

                const currentUser = await Auth.currentAuthenticatedUser();
                const session = await Auth.currentSession();
                const token = session.getAccessToken().getJwtToken();
                localStorage.setItem("scalar_token", token);

                setIsAuthenticated(true);
                setUser({
                    username: currentUser.username,
                    email: currentUser.attributes?.email,
                    picture: currentUser.attributes?.picture || `https://api.dicebear.com/7.x/avataaars/svg?seed=${currentUser.username}`
                });
                setActiveTab("OVERVIEW");
            } catch (err) {
                console.log("No active AWS session - checking local mock");
                const mockToken = localStorage.getItem("scalar_token");
                const mockUserStr = localStorage.getItem("scalar_user");

                if (mockToken && mockUserStr && mockToken.startsWith("mock-")) {
                    const mockUser = JSON.parse(mockUserStr);
                    setIsAuthenticated(true);
                    setUser(mockUser);
                } else {
                    setIsAuthenticated(false);
                    setUser(null);
                    localStorage.removeItem("scalar_token");
                    localStorage.removeItem("scalar_user");
                }
            } finally {
                setIsAuthenticating(false);
            }
        };

        checkUser();

        // Listen for Auth events (Login/Logout)
        const unsubscribe = Hub.listen("auth", ({ payload: { event, data } }) => {
            switch (event) {
                case "signIn":
                    checkUser();
                    break;
                case "signOut":
                    setIsAuthenticated(false);
                    setUser(null);
                    localStorage.removeItem("scalar_token");
                    setActiveTab("IDENTITY");
                    break;
            }
        });

        if (isAuthenticated && isPageVisible) {
            fetchConfig();
            fetchAvailableCategories();
            fetchLeaderboard();

            const configInterval = setInterval(fetchConfig, 10000);
            const leaderboardInterval = setInterval(fetchLeaderboard, 30000); // Less frequent leaderboard updates

            return () => {
                clearInterval(configInterval);
                clearInterval(leaderboardInterval);
                unsubscribe();
            };
        }

        return () => {
            unsubscribe();
        };
    }, [isAuthenticated, isPageVisible]);

    // Separate effect for trades polling to be more efficient
    useEffect(() => {
        const canPollTrades = isAuthenticated &&
            isPageVisible &&
            wallets.length > 0 &&
            (activeTab === "OVERVIEW" || activeTab === "REPLICATION");

        if (canPollTrades) {
            fetchTrades();
            const tradesInterval = setInterval(fetchTrades, 10000);
            return () => clearInterval(tradesInterval);
        }
    }, [isAuthenticated, isPageVisible, wallets.length, activeTab]);

    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const payment = urlParams.get('payment');
        if (payment === 'success') {
            alert("Payment Successful! One additional slot has been added to your account.");
            fetchConfig();
            window.history.replaceState({}, document.title, window.location.pathname);
        } else if (payment === 'cancel') {
            alert("Payment Cancelled.");
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }, [isAuthenticated]);

    const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || "");

    const getAuthHeaders = () => ({
        "Authorization": `Bearer ${localStorage.getItem("scalar_token") || "mock-token"}`,
        "Content-Type": "application/json",
    });

    const fetchOptions = (method: string = "GET", body?: BodyInit): RequestInit => ({
        method,
        headers: getAuthHeaders(),
        ...(body !== undefined && { body }),
    });

    const fetchConfig = async () => {
        try {
            const res = await fetch(`${API_BASE}/trading/config`, fetchOptions());
            if (res.ok) {
                const data = await res.json();
                const newWallets = data.tracked_wallets || [];
                setWallets(newWallets);
                setDisabledWallets(data.disabled_wallets || []);
                setTerminatedWallets(data.terminated_wallets || []);
                const skipStatsFromPoll = Date.now() - lastCapitalResetAt.current < 15000;
                if (data.stats && !skipStatsFromPoll) {
                    const b = Number(data.stats.balance);
                    const i = Number(data.stats.initial_balance);
                    setStats({
                        balance: Number.isFinite(b) ? b : 100,
                        initial_balance: Number.isFinite(i) ? i : 100,
                        subscriptionStatus: data.subscription_status || "free",
                        subscriptionId: data.subscription_id,
                        extraSlots: data.extra_slots || 0
                    } as any);

                    // Only initialize the input field if it's currently empty or at the default "100.0"
                    if (initialBalanceInput === "100.0" || initialBalanceInput === "") {
                        setInitialBalanceInput((Number.isFinite(i) ? i : 100).toString());
                    }

                    if (data.balance_threshold !== undefined) {
                        setBalanceThreshold(data.balance_threshold.toString());
                    }
                    if (data.daily_pnl_threshold !== undefined) {
                        setDailyPnlThreshold(data.daily_pnl_threshold.toString());
                    }
                    if (data.trading_mode !== undefined) {
                        setTradingMode(data.trading_mode);
                    }
                    if (data.live_polymarket_address !== undefined) {
                        setLivePolymarketAddress(data.live_polymarket_address || "");
                    }
                    if (data.user_profile) {
                        setUserProfile(data.user_profile);
                    }
                    (setStats as any)((prev: any) => ({
                        ...prev,
                        referralCode: data.referral_code,
                        referralCount: data.referral_count
                    }));
                }
                if (Array.isArray(data.balance_history) && !skipStatsFromPoll) setBalanceHistory(data.balance_history);
                if (data.filters) setFilters(data.filters);

                // Fetch profiles for new wallets
                newWallets.forEach((addr: string) => {
                    if (!profiles[addr]) fetchProfile(addr);
                });
            } else if (res.status === 401) {
                setIsAuthenticated(false);
                setUser(null);
                localStorage.removeItem("scalar_token");
                setActiveTab("IDENTITY");
            }
        } catch (error) { console.error("Failed to fetch config:", error); }
    };

    const fetchProfile = async (address: string) => {
        try {
            const res = await fetch(`${API_BASE}/profiles/${address}`, fetchOptions());
            if (res.ok) {
                const data = await res.json();
                if (data.username || data.displayName) {
                    setProfiles(prev => ({ ...prev, [address]: data }));
                }
            } else if (res.status === 401) {
                setIsAuthenticated(false);
                setUser(null);
                localStorage.removeItem("scalar_token");
                setActiveTab("IDENTITY");
            }
        } catch (error) { console.error("Failed to fetch profile:", error); }
    };

    const fetchTrades = async () => {
        try {
            const res = await fetch(`${API_BASE}/trading/trades`, fetchOptions());
            if (res.ok) {
                const data = await res.json();
                setTrades(data);
            } else if (res.status === 401) {
                setIsAuthenticated(false);
                setUser(null);
                localStorage.removeItem("scalar_token");
                setActiveTab("IDENTITY");
            }
        } catch (error) { console.error("Failed to fetch trades:", error); }
    };

    const fetchLeaderboard = async () => {
        try {
            const res = await fetch(`${API_BASE}/social/leaderboard`, fetchOptions());
            if (res.ok) {
                const data = await res.json();
                setLeaderboard(data);
            }
        } catch (error) { console.error("Failed to fetch leaderboard:", error); }
    };

    const fetchAvailableCategories = async () => {
        try {
            const res = await fetch(`${API_BASE}/intelligence/available-categories`, fetchOptions());
            if (res.ok) {
                const data = await res.json();
                setAvailableCategories(data.categories || []);
            } else if (res.status === 401) {
                setIsAuthenticated(false);
                setUser(null);
                localStorage.removeItem("scalar_token");
                setActiveTab("IDENTITY");
            }
        } catch (error) { console.error("Failed to fetch available categories:", error); }
    };

    useEffect(() => {
        if (!isAuthenticated) return;
        const fetchWhales = async () => {
            try {
                const res = await fetch(`${API_BASE}/intelligence/whales`, { headers: getAuthHeaders() });
                if (res.status === 401) return handleLogout();
                if (res.ok) {
                    const data = await res.json();
                    if (data && Array.isArray(data)) {
                        setWhales(prev => [...data, ...prev].slice(0, 10));
                    }
                }
            } catch (err) { console.error("Whale fetch error:", err); }
        };
        const fetchSignals = async () => {
            try {
                const res = await fetch(`${API_BASE}/intelligence/signals`, { headers: getAuthHeaders() });
                if (res.ok) {
                    const data = await res.json();
                    setSignals(data || []);
                }
            } catch (err) { console.error("Signal fetch error:", err); }
        };

        const fetchHeatmap = async () => {
            try {
                const res = await fetch(`${API_BASE}/intelligence/heatmap`, { headers: getAuthHeaders() });
                if (res.ok) {
                    const data = await res.json();
                    setHeatmap(data || []);
                }
            } catch (err) { console.error("Heatmap fetch error:", err); }
        };

        const fetchAIPortfolio = async () => {
            try {
                const res = await fetch(`${API_BASE}/ai/portfolio`, { headers: getAuthHeaders() });
                if (res.ok) {
                    const data = await res.json();
                    setAIPortfolio(data);
                }
            } catch (err) { console.error("AI Portfolio fetch error:", err); }
        };

        // Real-time WebSocket logic
        const wsUrl = `ws://${new URL(API_BASE).host}/ws/${user?.username || 'anon'}`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => console.info("WebSocket Tunnel Active");
        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === "WHALE_RADAR") {
                    setWhales(prev => [msg.data, ...prev].slice(0, 10));
                } else if (msg.type === "SOCIAL_FEED_UPDATE") {
                    // Logic to update social feed if needed
                } else if (msg.type === "ALPHA_STREAM_UPDATE") {
                    setSocialFeed(prev => [msg.data, ...prev].slice(0, 15));
                }
            } catch (e) { console.error("WS parse error", e); }
        };

        const whaleInterval = setInterval(fetchWhales, 60000); // Polling reduced to 1m fallback
        const signalInterval = setInterval(fetchSignals, 60000);
        const heatmapInterval = setInterval(fetchHeatmap, 300000);
        const aiInterval = setInterval(fetchAIPortfolio, 300000);

        fetchWhales();
        fetchSignals();
        fetchHeatmap();
        fetchAIPortfolio();

        return () => {
            clearInterval(whaleInterval);
            clearInterval(signalInterval);
            clearInterval(heatmapInterval);
            clearInterval(aiInterval);
            ws.close();
        };
    }, [isAuthenticated, API_BASE]);

    const addWallet = async () => {
        if (!newWallet) return;
        try {
            const res = await fetch(`${API_BASE}/wallets/add?address=${newWallet}`, fetchOptions("POST"));
            if (res.ok) {
                const data = await res.json();
                setWallets(data.wallets);
                if (data.status === "reactivated") {
                    alert("Node Reactivated: This address was previously terminated and has now been restored to active duty.");
                }
                setNewWallet("");
                fetchConfig(); // Refresh to update terminatedWallets and disabledWallets
                fetchProfile(newWallet);
            } else if (res.status === 401) {
                setIsAuthenticated(false);
                setUser(null);
                localStorage.removeItem("scalar_token");
                setActiveTab("IDENTITY");
            } else if (res.status === 402) {
                if (window.confirm("Address limit reached. Purchase an additional tracking slot for $5?")) {
                    handleExtraSlotPurchase();
                }
            } else if (res.status === 400) {
                alert("This address is already being tracked.");
            }
        } catch (error) { console.error("Failed to add wallet:", error); }
    };

    const handleExtraSlotPurchase = async () => {
        try {
            const res = await fetch(`${API_BASE}/stripe/create-checkout-session`, fetchOptions("POST"));
            if (res.ok) {
                const { url } = await res.json();
                if (url) {
                    window.location.href = url; // Redirect to Stripe Checkout
                } else {
                    alert("Failed to initiate Stripe Checkout.");
                }
            } else {
                const err = await res.json();
                console.error("Order creation failed:", err);
                alert(`Failed to create payment order: ${err.detail || "Unknown error"}`);
            }
        } catch (error) {
            console.error("Payment initiation failed:", error);
            alert("Could not initialize payment. Please check console for details.");
        }
    };

    const terminateWallet = async (address: string) => {
        const confirmed = window.confirm("Are you sure you want to terminate this wallet? Once terminated, it cannot be deleted and will still occupy a subscription slot, but all trade replication will stop.");
        if (!confirmed) return;

        try {
            const res = await fetch(`${API_BASE}/wallets/terminate?address=${address}`, fetchOptions("POST"));
            if (res.ok) {
                const data = await res.json();
                setWallets(data.wallets);
                if (data.terminated_wallets) setTerminatedWallets(data.terminated_wallets);
                if (selectedWallet === address) setSelectedWallet(null);
                fetchConfig(); // Refresh full state
            } else if (res.status === 401) {
                setIsAuthenticated(false);
                setUser(null);
                localStorage.removeItem("scalar_token");
                setActiveTab("IDENTITY");
            }
        } catch (error) { console.error("Failed to terminate wallet:", error); }
    };

    const addFilter = async (category?: string) => {
        const catToAdd = category || newFilter;
        if (!catToAdd) return;
        try {
            const res = await fetch(`${API_BASE}/filters/add?category=${catToAdd}`, fetchOptions("POST"));
            if (res.ok) {
                const data = await res.json();
                setFilters(data.filters);
                setNewFilter("");
            } else if (res.status === 401) {
                setIsAuthenticated(false);
                setUser(null);
                localStorage.removeItem("scalar_token");
                setActiveTab("IDENTITY");
            }
        } catch (error) { console.error("Failed to add filter:", error); }
    };

    const updateFilter = async (newFilters: any) => {
        try {
            const res = await fetch(`${API_BASE}/trading/config/update`, {
                method: "POST",
                headers: getAuthHeaders(),
                body: JSON.stringify({ filters: newFilters }),
            });
            if (res.ok) {
                const data = await res.json();
                setFilters(data.filters);
            } else if (res.status === 401) {
                setIsAuthenticated(false);
                setUser(null);
                localStorage.removeItem("scalar_token");
                setActiveTab("IDENTITY");
            }
        } catch (error) { console.error("Failed to update filter:", error); }
    };

    const removeFilter = async (category: string) => {
        try {
            const res = await fetch(`${API_BASE}/filters/remove?category=${category}`, fetchOptions("POST"));
            if (res.ok) {
                const data = await res.json();
                setFilters(data.filters);
            } else if (res.status === 401) {
                setIsAuthenticated(false);
                setUser(null);
                localStorage.removeItem("scalar_token");
                setActiveTab("IDENTITY");
            }
        } catch (error) { console.error("Failed to remove filter:", error); }
    };

    const toggleWalletTracking = async (address: string) => {
        try {
            const res = await fetch(`${API_BASE}/wallets/toggle?address=${address}`, fetchOptions("POST"));
            if (res.ok) {
                const data = await res.json();
                setDisabledWallets(data.disabled_wallets);
            } else if (res.status === 401) {
                setIsAuthenticated(false);
                setUser(null);
                localStorage.removeItem("scalar_token");
                setActiveTab("IDENTITY");
            }
        } catch (error) { console.error("Failed to toggle wallet tracking:", error); }
    };

    const updateConfigSettings = async (params: { initial_balance?: number, balance_threshold?: number, daily_pnl_threshold?: number, trading_mode?: string, polymarket_address?: string }) => {
        try {
            let url = `${API_BASE}/config/update?`;
            if (params.initial_balance !== undefined) url += `initial_balance=${params.initial_balance}&`;
            if (params.balance_threshold !== undefined) url += `balance_threshold=${params.balance_threshold}&`;
            if (params.daily_pnl_threshold !== undefined) url += `daily_pnl_threshold=${params.daily_pnl_threshold}&`;
            if (params.trading_mode !== undefined) url += `trading_mode=${params.trading_mode}&`;
            if (params.polymarket_address !== undefined) url += `polymarket_address=${params.polymarket_address}`;

            const res = await fetch(url, fetchOptions("POST"));
            if (res.ok) {
                const data = await res.json();
                if (params.initial_balance !== undefined) {
                    const newStats = data.stats || {};
                    const balance = Number(newStats.balance);
                    const initial_balance = Number(newStats.initial_balance);
                    setStats({
                        balance: Number.isFinite(balance) ? balance : params.initial_balance,
                        initial_balance: Number.isFinite(initial_balance) ? initial_balance : params.initial_balance,
                    } as any);
                    setBalanceHistory([{ timestamp: Date.now() / 1000, balance: Number.isFinite(balance) ? balance : params.initial_balance }]);
                    setTrades([]);
                    lastCapitalResetAt.current = Date.now();
                }
                fetchTrades();
                fetchConfig();
                if (params.daily_pnl_threshold !== undefined) fetchLeaderboard();
                console.log("Configuration updated");
            } else if (res.status === 401) {
                setIsAuthenticated(false);
                setUser(null);
                localStorage.removeItem("scalar_token");
                localStorage.removeItem("scalar_user");
                setActiveTab("IDENTITY");
            }
        } catch (error) { console.error("Failed to update config:", error); }
    };

    const handleUpdateInitialBalance = async () => {
        const amount = parseFloat(initialBalanceInput);
        if (isNaN(amount)) return;
        if (window.confirm(`This will RESET all current trade history and set the initial capital to $${amount}. Proceed?`)) {
            updateConfigSettings({ initial_balance: amount });
        }
    };

    const handleUpdateBalanceThreshold = () => {
        const val = parseFloat(balanceThreshold);
        if (!isNaN(val)) updateConfigSettings({ balance_threshold: val });
    };

    const handleUpdateDailyPnlThreshold = () => {
        const val = parseFloat(dailyPnlThreshold);
        if (!isNaN(val)) updateConfigSettings({ daily_pnl_threshold: val });
    };

    const handleUpdateTradingMode = (mode: "paper" | "live") => {
        updateConfigSettings({ trading_mode: mode });
    };

    const handleUpdatePolymarketAddress = () => {
        updateConfigSettings({ polymarket_address: livePolymarketAddress });
    };

    const filteredTrades = useMemo(() => {
        return trades
            .filter(t => {
                const matchesWallet = selectedWallet ? t.wallet.toLowerCase() === selectedWallet.toLowerCase() : true;
                const matchesSearch = searchAddress ? t.wallet.toLowerCase().includes(searchAddress.toLowerCase()) || t.market.toLowerCase().includes(searchAddress.toLowerCase()) : true;
                const matchesSide = sideFilter === "ALL" ? true : t.side === sideFilter;
                return matchesWallet && matchesSearch && matchesSide;
            });
    }, [trades, selectedWallet, searchAddress, sideFilter]);

    const handleLogout = async () => {
        // Clear local state first for immediate UI response
        console.log("Initiating logout...");
        setIsAuthenticated(false);
        setUser(null);
        localStorage.removeItem("scalar_token");
        localStorage.removeItem("scalar_user");
        setActiveTab("IDENTITY");

        try {
            if (awsConfig.USER_POOL_ID && awsConfig.USER_POOL_ID !== "us-east-1_dummy") {
                console.log("Terminating Cognito session via Amplify...");
                // Note: Auth.signOut() with OAuth will redirect to the logout endpoint
                await Auth.signOut();
            }
        } catch (err) {
            console.error("Cognito sign out error (force clearing local):", err);
        } finally {
            // Force clear again just in case
            localStorage.clear();
            console.log("Logout complete (local state forced).");
        }
    };

    const forceClearSession = () => {
        const confirmed = window.confirm("This will force clear ALL local session data and reload the application. Use this if you are stuck in a login/logout loop. Proceed?");
        if (!confirmed) return;

        localStorage.clear();
        sessionStorage.clear();
        // Clear cookies if possible (Amplify uses them sometimes)
        document.cookie.split(";").forEach((c) => {
            document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
        });
        window.location.href = window.location.origin + "/";
    };

    const handleSocialLogin = async (provider: "Google" | "Twitter") => {
        const fallbackMockLogin = async () => {
            console.warn("Using mock social login");
            try {
                const res = await fetch(`${API_BASE}/auth/mock/login`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username: `${provider.toLowerCase()}_user` })
                });
                if (res.ok) {
                    const data = await res.json();
                    const mockUser = {
                        username: data.user_id,
                        email: `${provider.toLowerCase()}@example.com`,
                        picture: `https://api.dicebear.com/7.x/avataaars/svg?seed=${provider}`
                    };
                    setIsAuthenticated(true);
                    setUser(mockUser);
                    localStorage.setItem("scalar_token", data.access_token);
                    localStorage.setItem("scalar_user", JSON.stringify(mockUser));
                    setActiveTab("OVERVIEW");
                }
            } catch (err) {
                console.error("Mock login via backend failed:", err);
            }
        };

        // Use mock login if explicitly enabled or if real config is missing
        const isMockEnabled = process.env.NEXT_PUBLIC_MOCK_AUTH === "true";
        if (isMockEnabled || !awsConfig.USER_POOL_ID || !awsConfig.USER_POOL_CLIENT_ID || awsConfig.USER_POOL_ID.includes("dummy")) {
            fallbackMockLogin();
            return;
        }

        try {
            await Auth.federatedSignIn({ provider: provider as any });
        } catch (err) {
            console.error("Federated sign-in failed, falling back to mock login:", err);
            fallbackMockLogin();
        }
    };

    return (
        <main className="min-h-screen bg-[#050505] text-white font-sans selection:bg-white/20">
            {/* Sidebar Navigation */}
            <aside className="fixed left-0 top-0 bottom-0 w-[260px] bg-black border-r border-white/10 flex flex-col z-50">
                <div className="p-8 flex items-center gap-3">
                    <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center shadow-lg">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M12 4L4 12L12 20L20 12L12 4Z" stroke="black" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    </div>
                    <div>
                        <span className="text-[18px] font-black tracking-tight block leading-none">Pclonecopy</span>
                        <span className="text-[9px] font-black uppercase text-white/30 tracking-[0.2em] mt-1 block">Institutional</span>
                    </div>
                </div>

                <nav className="flex-1 px-4 py-6 space-y-1.5">
                    {[
                        { id: "IDENTITY", label: "Identity", icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 00-4-4H9a4 4 0 00-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>, public: true },
                        { id: "OVERVIEW", label: "Dashboard", icon: <Icons.Dashboard />, protected: true },
                        { id: "FLEET", label: "Node Matrix", icon: <Icons.Fleet />, protected: true },
                        { id: "REPLICATION", label: "Stream", icon: <Icons.Matrix />, protected: true },
                        /* Phase 2-5 items hidden for Phase 1 release */
                        // { id: "STRATEGY", label: "Intel Engine", icon: <Icons.Strategy />, protected: true },
                        // { id: "SOCIAL", label: "Social Matrix", icon: <Icons.Messages />, protected: true },
                        // { id: "SUBSCRIPTION", label: "Subscription", icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" /></svg>, protected: true },
                        { id: "SETTINGS", label: "Settings", icon: <Icons.Settings />, protected: true }
                    ].map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id as any)}
                            disabled={tab.protected && !isAuthenticated}
                            className={`w-full flex items-center gap-4 px-5 py-3.5 rounded-lg transition-all font-bold text-[12px] uppercase tracking-wider group ${activeTab === tab.id ? 'bg-white text-black shadow-xl scale-[1.02]' : 'text-white/40 hover:text-white hover:bg-white/5'} ${tab.protected && !isAuthenticated ? 'opacity-30 cursor-not-allowed' : ''}`}
                        >
                            <span className={`transition-colors ${activeTab === tab.id ? 'text-black' : 'text-white/20 group-hover:text-white/40'}`}>{tab.icon}</span>
                            {tab.label}
                        </button>
                    ))}
                    {isAuthenticated && (
                        <button
                            onClick={handleLogout}
                            className="w-full flex items-center gap-4 px-5 py-3.5 rounded-lg transition-all font-bold text-[12px] uppercase tracking-wider text-white/40 hover:text-rose-500 hover:bg-white/5"
                        >
                            <span className="text-white/20 group-hover:text-rose-500"><Icons.Logout /></span>
                            Logout
                        </button>
                    )}
                </nav>

                <div className="p-6 border-t border-white/5">
                    <div className="bg-white/5 rounded-2xl p-4 border border-white/5">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-8 h-8 rounded-lg bg-[#0075ff]/20 flex items-center justify-center">
                                <Icons.Settings />
                            </div>
                            <span className="text-[11px] font-black uppercase tracking-widest text-white/60">System Ready</span>
                        </div>
                        <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                            <div className="h-full bg-[#01b574] w-full" />
                        </div>
                    </div>
                </div>
            </aside>

            {/* Top Header */}
            <header className="fixed top-0 right-0 left-[260px] h-20 bg-[#060b26]/50 backdrop-blur-md border-b border-white/5 flex items-center justify-between px-10 z-40">
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 text-white/40 text-[12px] font-bold">
                        <span>Pclonecopy</span>
                        <span>/</span>
                        <span className="text-white uppercase tracking-widest">{activeTab}</span>
                    </div>
                </div>

                <div className="flex items-center gap-6">
                    {isAuthenticated && user && (
                        <div className="flex items-center gap-3 pl-2">
                            <div className="text-right hidden sm:block">
                                <p className="text-[12px] font-black text-white/80 leading-none">{(userProfile.name || user.email || user.username).toUpperCase()}</p>
                                <div className="flex items-center gap-2 mt-1 justify-end">
                                    <p className={`text-[10px] font-bold ${(stats as any).subscriptionStatus === 'pro' ? 'text-[#01b574]' : 'text-white/40'}`}>
                                        {(stats as any).subscriptionStatus === 'pro' ? 'PRO ACCOUNT' : 'FREE ACCOUNT'}
                                    </p>
                                    {(stats as any).subscriptionStatus === 'free' && (
                                        <button
                                            onClick={() => window.location.href = `${API_BASE}/subscribe`}
                                            className="px-2 py-0.5 bg-[#0075ff] rounded text-[8px] font-black text-white hover:bg-[#0075ff]/80 transition-colors"
                                        >
                                            UPGRADE
                                        </button>
                                    )}
                                </div>
                            </div>
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#1a1f37] to-[#0f1535] border border-white/10 flex items-center justify-center overflow-hidden">
                                <img src={userProfile.picture || user.picture || `https://api.dicebear.com/7.x/avataaars/svg?seed=${user.username}`} alt="Avatar" className="w-8 h-8 opacity-80" />
                            </div>
                        </div>
                    )}
                    {!isAuthenticated && (
                        <button
                            onClick={() => setActiveTab("IDENTITY")}
                            className="px-5 py-2.5 bg-white/10 border border-white/20 rounded-lg text-[11px] font-black uppercase tracking-widest text-white hover:bg-white/20 transition-all"
                        >
                            Login
                        </button>
                    )}
                </div>
            </header>

            {/* Main Content Area */}
            <div className="ml-[260px] pt-32 px-12 pb-20 min-h-screen">
                {!isAuthenticated && activeTab !== "IDENTITY" && (
                    <div className="flex flex-col items-center justify-center h-[calc(100vh-160px)] text-center">
                        <div className="max-w-md text-center space-y-6">
                            <h2 className="text-2xl font-black text-white tracking-tighter uppercase italic">Institutional Access Only</h2>
                            <p className="text-sm text-white/40 leading-relaxed italic">
                                This terminal section is restricted to authorized entities. Please authenticate via the IDENTITY tab to proceed with cluster management and engine monitoring.
                            </p>
                            <button
                                onClick={() => setActiveTab("IDENTITY")}
                                className="px-8 py-3 bg-white text-black font-black text-xs tracking-widest uppercase hover:bg-white/80 transition-colors"
                            >
                                GO TO IDENTITY
                            </button>
                        </div>
                    </div>
                )}

                {activeTab === "IDENTITY" && (
                    <div className="flex flex-col items-center justify-center h-[calc(100vh-160px)]">
                        <div className="max-w-4xl w-full grid grid-cols-1 md:grid-cols-2 gap-12 bg-white/5 p-12 rounded-2xl border border-white/10">
                            <div className="space-y-6">
                                <h1 className="text-4xl font-black text-white tracking-tighter italic uppercase">Terminal Identity</h1>
                                {isAuthenticated && user ? (
                                    <div className="space-y-8 animate-in fade-in slide-in-from-left-4">
                                        <div className="flex items-center gap-6">
                                            <div className="w-24 h-24 rounded-2xl bg-white/10 border border-white/10 p-1 flex items-center justify-center overflow-hidden shadow-2xl">
                                                <img src={userProfile.picture || user.picture} alt="Profile" className="w-full h-full rounded-xl object-cover" />
                                            </div>
                                            <div>
                                                <h3 className="text-[18px] font-black text-white tracking-tight leading-none mb-2 capitalize">{userProfile.name || user.username}</h3>
                                                <p className="text-[12px] font-bold text-white/40 mb-3">{user.email}</p>
                                                <span className="px-3 py-1 bg-[#01b574]/10 border border-[#01b574]/20 rounded-full text-[9px] font-black text-[#01b574] uppercase tracking-widest">Authorized</span>
                                            </div>
                                        </div>
                                        <div className="flex flex-col gap-3 pt-6">
                                            <button
                                                onClick={handleLogout}
                                                className="w-full py-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-500 font-black text-[10px] tracking-widest uppercase hover:bg-rose-500 hover:text-white transition-all shadow-lg shadow-rose-500/10"
                                            >
                                                De-Authorize Terminal
                                            </button>
                                            <button
                                                onClick={forceClearSession}
                                                className="w-full py-3 text-white/20 hover:text-white/40 font-bold text-[9px] uppercase tracking-[0.2em] transition-colors"
                                            >
                                                Force Clear Session & Reload
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    <>
                                        <p className="text-sm text-white/40 leading-relaxed">
                                            Authenticate your session to sync fleet nodes, engine logic, and performance metrics across the cluster.
                                        </p>
                                        <div className="space-y-4 pt-4">
                                            <button
                                                onClick={() => handleSocialLogin("Google")}
                                                className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-white text-black font-black text-xs tracking-widest uppercase hover:bg-white/80 transition-all active:scale-[0.98] shadow-xl"
                                            >
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" /><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" /><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05" /><path d="M12 5.38c1.62 0 3.06.56 4.21 1.66l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" /><path d="M1 1h22v22H1z" fill="none" />
                                                </svg>
                                                Login with Google
                                            </button>
                                            {/* 
                                            <button
                                                onClick={() => handleSocialLogin("Twitter")}
                                                className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-[#1DA1F2] text-white font-black text-xs tracking-widest uppercase hover:bg-[#1DA1F2]/80 transition-all active:scale-[0.98] shadow-xl shadow-[#1DA1F2]/20"
                                            >
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                                    <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.84 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z" />
                                                </svg>
                                                Login with Twitter
                                            </button>
                                            */}
                                        </div>
                                    </>
                                )}
                            </div>
                            <div className="hidden md:flex flex-col justify-center items-center border-l border-white/10 pl-12 space-y-4">
                                <div className="w-24 h-24 bg-white/10 rounded-3xl rotate-12 flex items-center justify-center border border-white/10 shadow-2xl backdrop-blur-xl group hover:rotate-0 transition-all">
                                    <span className="text-5xl text-white group-hover:scale-110">🔒</span>
                                </div>
                                <div className="text-center">
                                    <p className="text-[10px] font-black text-white uppercase tracking-[0.3em] mb-1">Grid Protection</p>
                                    <p className="text-[9px] text-white/20 italic font-mono uppercase">Multi-Factor Sharding Enabled</p>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {isAuthenticated && activeTab === "OVERVIEW" && (
                    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        {/* KPI Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
                            {[
                                { label: "Performance Delta", val: `$${(stats.balance - stats.initial_balance).toFixed(2)}`, icon: <Icons.Dashboard /> },
                                { label: "System Liquidity", val: `$${stats.balance.toLocaleString()}`, icon: <Icons.Strategy /> },
                                { label: "Active Nodes", val: wallets.filter(w => !disabledWallets.includes(w)).length, icon: <Icons.Fleet /> },
                                { label: "Ingestion Vol", val: trades.length, icon: <Icons.Matrix /> }
                            ].map((item, i) => (
                                <div key={i} className="bg-white/[0.03] border border-white/10 p-6 rounded-xl flex items-center justify-between shadow-sm">
                                    <div>
                                        <p className="text-[10px] font-black text-white/30 uppercase tracking-widest mb-1">{item.label}</p>
                                        <div className="flex items-center gap-2">
                                            <h3 className="text-[20px] font-black text-white">{item.val}</h3>
                                        </div>
                                    </div>
                                    <div className="w-10 h-10 bg-white/5 border border-white/5 rounded-xl flex items-center justify-center text-white">
                                        {item.icon}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Middle Performance Grid */}
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                            {/* Performance Chart - real-time from balance_history */}
                            <div className="lg:col-span-8 bg-black border border-white/10 p-8 rounded-xl shadow-xl">
                                <h3 className="text-[14px] font-black text-white uppercase tracking-wider mb-1">Execution Trajectory</h3>
                                <p className="text-[11px] text-white/30 mb-10 font-bold italic uppercase">Balance over time (real-time)</p>
                                <div className="h-[220px] flex items-end justify-between px-4 gap-3">
                                    {(() => {
                                        const hist = balanceHistory.length > 0 ? balanceHistory : [{ timestamp: 0, balance: stats.initial_balance }, { timestamp: 1, balance: stats.balance }];
                                        const minB = Math.min(...hist.map(h => h.balance), stats.initial_balance);
                                        const maxB = Math.max(...hist.map(h => h.balance), stats.initial_balance, stats.initial_balance * 1.01);
                                        const range = maxB - minB || 1;
                                        const points = hist.slice(-24);
                                        if (points.length === 0) return <div className="flex-1 flex items-center justify-center text-white/20 text-[11px] font-bold uppercase">Awaiting data</div>;
                                        return points.map((h, i) => {
                                            const pct = Math.min(100, Math.max(0, ((h.balance - minB) / range) * 100));
                                            return (
                                                <div key={`${h.timestamp}-${i}`} className="flex-1 rounded-sm transition-all duration-700 bg-white/5 relative group hover:bg-white/20" style={{ height: `${pct}%` }} title={`$${h.balance.toFixed(2)}`}>
                                                    <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity rounded-sm" />
                                                </div>
                                            );
                                        });
                                    })()}
                                </div>
                            </div>

                            {/* Signal Gauge */}
                            <div className="lg:col-span-4 bg-black border border-white/10 p-8 rounded-xl shadow-xl flex flex-col items-center justify-center">
                                <h3 className="text-[14px] font-black text-white uppercase tracking-wider self-start mb-1">Signal Grade</h3>
                                <p className="text-[11px] text-white/30 self-start mb-8 font-bold italic uppercase">Real-time quality</p>

                                <div className="relative w-full aspect-square flex items-center justify-center max-w-[170px]">
                                    <svg viewBox="0 0 100 100" className="w-full rotate-[-90deg]">
                                        <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="8" />
                                        <circle cx="50" cy="50" r="45" fill="none" stroke="white" strokeWidth="8" strokeDasharray="282.7" strokeDashoffset={282.7 * (1 - 0.95)} strokeLinecap="square" className="transition-all duration-1000" />
                                    </svg>
                                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                                        <span className="text-[42px] font-black text-white tracking-tighter block leading-none">95<span className="text-[18px] opacity-20">%</span></span>
                                    </div>
                                </div>

                                <div className="w-full grid grid-cols-2 gap-3 mt-10">
                                    <div className="bg-white/[0.02] p-4 rounded-xl border border-white/5">
                                        <p className="text-[8px] font-black text-white/20 uppercase tracking-widest text-center">Latency</p>
                                        <p className="text-[14px] font-black text-white text-center mt-1">0.1ms</p>
                                    </div>
                                    <div className="bg-white/[0.02] p-4 rounded-xl border border-white/5">
                                        <p className="text-[8px] font-black text-white/20 uppercase tracking-widest text-center">Slippage</p>
                                        <p className="text-[14px] font-black text-white text-center mt-1">0.0%</p>
                                    </div>
                                </div>
                            </div>

                            {/* Phase 3+ Intelligence features hidden in Phase 1 release */}
                            {/* Whale Radar & Heatmap HUD */}
                            {/*
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                                <div className="bg-white/[0.03] border border-white/10 p-6 rounded-2xl">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="text-[12px] font-black uppercase tracking-widest flex items-center gap-2">
                                            Whale Radar <span className="w-2 h-2 rounded-full bg-[#0075ff] animate-pulse" />
                                        </h3>
                                        <span className="text-[9px] font-black text-white/20 uppercase">Smart Money Flow</span>
                                    </div>
                                    <div className="space-y-2">
                                        {whales.length === 0 ? (
                                            <div className="py-6 text-center text-white/10 font-black uppercase text-[10px] tracking-widest italic">Scanning Clusters...</div>
                                        ) : (
                                            whales.slice(0, 4).map((w) => (
                                                <div key={w.id} className="p-3 bg-white/[0.02] border border-white/5 rounded-xl flex items-center justify-between group">
                                                    <span className={`text-[8px] font-black px-1.5 py-0.5 rounded ${w.classification?.includes('Whale') ? 'bg-rose-500/20 text-rose-500' : 'bg-[#0075ff]/20 text-[#0075ff]'} uppercase tracking-widest`}>
                                                        {w.classification}
                                                    </span>
                                                    <p className="text-[10px] font-bold text-white truncate max-w-[120px] opacity-60">{w.market}</p>
                                                    <span className="text-[10px] font-black text-[#01b574] leading-none">${(w.value / 1000).toFixed(0)}K</span>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>

                                <div className="bg-white/[0.03] border border-white/10 p-6 rounded-2xl">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="text-[12px] font-black uppercase tracking-widest flex items-center gap-2">
                                            Retail Heatmap <span className="w-2 h-2 rounded-full bg-[#ff7e00] animate-pulse" />
                                        </h3>
                                        <span className="text-[9px] font-black text-white/20 uppercase">Market Crowdedness</span>
                                    </div>
                                    <div className="space-y-2">
                                        {heatmap.length === 0 ? (
                                            <div className="py-6 text-center text-white/10 font-black uppercase text-[10px] tracking-widest italic">Calculating Proximity...</div>
                                        ) : (
                                            heatmap.slice(0, 4).map((h, i) => (
                                                <div key={i} className="p-3 bg-white/[0.02] border border-white/5 rounded-xl flex items-center justify-between">
                                                    <p className="text-[10px] font-bold text-white truncate max-w-[120px]">{h.market}</p>
                                                    <div className="flex-1 mx-4 h-1 bg-white/5 rounded-full overflow-hidden">
                                                        <div className="h-full bg-gradient-to-r from-[#01b574] to-rose-500" style={{ width: `${h.retail_ratio * 100}%` }} />
                                                    </div>
                                                    <span className="text-[10px] font-black text-white/40">{Math.round(h.retail_ratio * 100)}% Retail</span>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                            </div>
                            */}

                            {/* Predictive Intelligence Grid */}
                            {/*
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                <div className="lg:col-span-2 bg-black border border-white/10 p-8 rounded-2xl shadow-xl">
                                    <h3 className="text-[14px] font-black text-white uppercase tracking-wider mb-1">Predictive Alpha Signals</h3>
                                    <p className="text-[11px] text-white/30 mb-8 font-bold italic uppercase">Whale behavior forecast models</p>

                                    <div className="space-y-4">
                                        {signals.length === 0 ? (
                                            <div className="py-12 text-center text-white/10 font-black uppercase text-[11px] tracking-[0.3em]">No Alpha Detected</div>
                                        ) : (
                                            signals.map((sig) => (
                                                <div key={sig.id} className="p-5 bg-white/[0.02] border border-white/5 rounded-2xl flex items-center justify-between hover:bg-white/5 transition-all">
                                                    <div className="flex items-center gap-6">
                                                        <div className="relative w-12 h-12 flex items-center justify-center">
                                                            <svg viewBox="0 0 100 100" className="w-full absolute rotate-[-90deg]">
                                                                <circle cx="50" cy="50" r="48" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="4" />
                                                                <circle cx="50" cy="50" r="48" fill="none" stroke="#0075ff" strokeWidth="4" strokeDasharray="301.6" strokeDashoffset={301.6 * (1 - sig.confidence / 100)} />
                                                            </svg>
                                                            <span className="text-[10px] font-black text-white">{sig.confidence}%</span>
                                                        </div>
                                                        <div>
                                                            <div className="flex items-center gap-3 mb-1">
                                                                <span className="px-2 py-0.5 bg-[#0075ff]/10 text-[#0075ff] text-[8px] font-black uppercase tracking-widest rounded">{sig.type}</span>
                                                                <span className="text-[10px] text-white/20 font-bold uppercase">{new Date(sig.timestamp * 1000).toLocaleTimeString()}</span>
                                                            </div>
                                                            <p className="text-[12px] font-black text-white tracking-tight">{sig.market}</p>
                                                            <p className="text-[10px] text-white/40 italic font-bold mt-1">{sig.reason}</p>
                                                        </div>
                                                    </div>
                                                    <button className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-[9px] font-black uppercase tracking-widest transition-all">Execute Signal</button>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>

                                {/* Market Intensity Gauge */}
                            {/*
                                <div className="bg-black border border-white/10 p-8 rounded-2xl shadow-xl flex flex-col items-center justify-center">
                                    <h3 className="text-[14px] font-black text-white uppercase tracking-wider self-start mb-1">Cluster Intensity</h3>
                                    <p className="text-[11px] text-white/30 self-start mb-8 font-bold italic uppercase">Whale density index</p>

                                    <div className="space-y-6 w-full">
                                        {[
                                            { label: "Institutional Titan", val: whales.filter(w => w.classification === "Institutional Titan").length, max: 5 },
                                            { label: "Polymarket Whale", val: whales.filter(w => w.classification === "Market Mover").length, max: 10 },
                                            { label: "Predictive Signals", val: signals.length, max: 8 }
                                        ].map((c) => (
                                            <div key={c.label}>
                                                <div className="flex justify-between items-center mb-2">
                                                    <span className="text-[9px] font-black text-white/40 uppercase tracking-widest">{c.label}</span>
                                                    <span className="text-[11px] font-black text-white">{c.val}</span>
                                                </div>
                                                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                                                    <div className="h-full bg-[#0075ff]" style={{ width: `${(c.val / c.max) * 100}%` }} />
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    <div className="mt-12 p-4 bg-[#01b574]/5 border border-[#01b574]/10 rounded-xl w-full">
                                        <p className="text-[9px] font-black text-[#01b574] uppercase tracking-widest text-center">Liquidity Status: High</p>
                                    </div>
                                </div>
                            </div>
                            */}
                        </div>

                        {/* Bottom Operational Grid */}
                        <div className="grid grid-cols-1 gap-6">
                            {/* Fleet Table */}
                            <div className="bg-[#1a1f37]/50 border border-white/10 p-8 rounded-3xl shadow-xl">
                                <div className="flex items-center justify-between mb-8">
                                    <h3 className="text-[16px] font-black text-white uppercase tracking-wider">Unit Network</h3>
                                    <button onClick={addWallet} className="bg-[#0075ff] hover:bg-[#0075ff]/80 text-white px-5 py-2.5 rounded-xl text-[11px] font-black uppercase tracking-widest flex items-center gap-2 transition-all">
                                        <Icons.Plus /> Register Node
                                    </button>
                                </div>

                                <div className="space-y-3">
                                    {wallets.length === 0 ? (
                                        <div className="py-20 text-center text-white/10 border-2 border-dashed border-white/5 rounded-2xl font-black uppercase tracking-widest italic">Awaiting node entry</div>
                                    ) : (
                                        wallets.map((addr, i) => {
                                            const isTerminated = terminatedWallets.includes(addr);
                                            return (
                                                <div key={addr} className={`flex items-center justify-between px-6 py-4 bg-white/[0.02] border border-white/5 rounded-2xl transition-all group ${isTerminated ? 'opacity-40 grayscale' : 'hover:bg-white/[0.04]'}`}>
                                                    <div className="flex items-center gap-5">
                                                        <div className="w-9 h-9 rounded-lg bg-[#1a1f37] border border-white/10 flex items-center justify-center">
                                                            <img src={`https://api.dicebear.com/7.x/pixel-art/svg?seed=${addr}`} className="w-6 h-6 opacity-40" />
                                                        </div>
                                                        <div>
                                                            <p className="text-[13px] font-bold text-white font-mono">{addr.slice(0, 14)}...</p>
                                                            <p className="text-[9px] text-white/20 font-black uppercase">REPLICATION UNIT {i + 1}</p>
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center gap-8">
                                                        <div className="hidden md:flex flex-col gap-1 w-24">
                                                            <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                                                                <div className="h-full bg-[#0075ff]" style={{ width: `${Math.floor(Math.random() * 40 + 60)}%` }} />
                                                            </div>
                                                        </div>
                                                        {isTerminated ? (
                                                            <span className="text-rose-500 text-[10px] font-black uppercase tracking-widest">Terminated</span>
                                                        ) : (
                                                            <>
                                                                <span className="text-[#01b574] text-[10px] font-black uppercase tracking-widest hidden sm:block">Locked</span>
                                                                <button onClick={() => terminateWallet(addr)} className="text-white/10 hover:text-rose-500 transition-colors opacity-0 group-hover:opacity-100" title="Terminate Tracking"><Icons.Trash /></button>
                                                            </>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        })
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {isAuthenticated && activeTab === "FLEET" && (
                    <div className="animate-in fade-in zoom-in-95 duration-500 max-w-5xl mx-auto">
                        <div className="flex items-center justify-between mb-8">
                            <div>
                                <h2 className="text-[24px] font-black uppercase tracking-tighter">Node Matrix</h2>
                                <p className="text-white/30 text-[11px] font-bold italic">Cluster management and individual tracking control.</p>
                            </div>
                            <div className="px-5 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white/60 text-[10px] font-black uppercase tracking-widest">
                                Status: <span className="text-white">Active</span>
                            </div>
                        </div>

                        <section className="bg-black border border-white/10 p-10 rounded-2xl shadow-2xl">
                            <form onSubmit={(e) => { e.preventDefault(); addWallet(); }} className="flex gap-4 mb-12">
                                <input
                                    value={newWallet}
                                    onChange={(e) => setNewWallet(e.target.value)}
                                    placeholder="Inject Source Address (0x...)"
                                    className="flex-1 bg-white/5 border border-white/10 rounded-xl px-6 py-5 text-[14px] font-bold outline-none focus:border-white focus:bg-white/10 transition-all font-mono text-white placeholder:text-white/20"
                                />
                                <button type="submit" className="px-10 bg-white text-black rounded-xl font-black text-[11px] uppercase tracking-widest transition-all hover:bg-white/90 active:scale-95 whitespace-nowrap">
                                    Inject Node
                                </button>
                            </form>

                            <div className="space-y-3">
                                {wallets.map((addr, i) => {
                                    const isTerminated = terminatedWallets.includes(addr);
                                    const isDisabled = disabledWallets.includes(addr);

                                    return (
                                        <div key={addr} className={`p-4 bg-white/[0.02] border border-white/10 rounded-xl flex items-center justify-between hover:border-white/30 transition-all group ${(isTerminated || isDisabled) ? 'opacity-40 grayscale' : ''}`}>
                                            <div className="flex items-center gap-5 overflow-hidden flex-1">
                                                <div
                                                    className="bg-white rounded-lg flex items-center justify-center shrink-0 overflow-hidden"
                                                    style={{ width: '40px', height: '40px', minWidth: '40px' }}
                                                >
                                                    {profiles[addr]?.image ? (
                                                        <img src={profiles[addr].image} className="w-full h-full object-cover" />
                                                    ) : (
                                                        <img src={`https://api.dicebear.com/7.x/pixel-art/svg?seed=${addr}`} className="w-7 h-7 opacity-80" />
                                                    )}
                                                </div>
                                                <div className="min-w-0 flex-1">
                                                    <div className="flex items-center gap-3">
                                                        <p className="text-[13px] font-black text-white font-mono truncate">
                                                            {profiles[addr]?.username || profiles[addr]?.displayName || (addr.length > 20 ? `${addr.substring(0, 8)}...${addr.substring(addr.length - 8)}` : addr)}
                                                        </p>
                                                        <a
                                                            href={`https://polymarket.com/profile/${addr}`}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="text-white/20 hover:text-white transition-colors"
                                                            title="View Polymarket Profile"
                                                        >
                                                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2 2V8a2 2 0 0 1 2-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" /></svg>
                                                        </a>
                                                    </div>
                                                    <p className="text-[10px] text-white/40 font-mono truncate mb-1">
                                                        {(profiles[addr]?.username || profiles[addr]?.displayName) ? (profiles[addr].proxyWallet || addr) : "Anon Node"}
                                                    </p>
                                                    {profiles[addr]?.bio && (
                                                        <p className="text-[10px] text-white/30 italic truncate mb-1 leading-tight">"{profiles[addr].bio}"</p>
                                                    )}
                                                    <div className="flex items-center gap-4">
                                                        <span className="text-[9px] font-black text-white/20 tracking-widest uppercase">Sequence {i + 1}</span>
                                                        {!isTerminated && !isDisabled && (
                                                            <>
                                                                <span className="w-1 h-1 bg-white/10 rounded-full" />
                                                                <div className="flex items-center gap-3 bg-white/5 px-3 py-1 rounded-lg">
                                                                    <span className="text-[8px] font-black text-white/40 uppercase tracking-widest">Weight</span>
                                                                    <input
                                                                        type="range"
                                                                        min="1"
                                                                        max="100"
                                                                        value={allocationWeights[addr] || "50"}
                                                                        onChange={(e) => handleUpdateAllocation(addr, e.target.value)}
                                                                        className="w-16 h-1 bg-white/10 rounded-full appearance-none cursor-pointer accent-[#0075ff]"
                                                                    />
                                                                    <span className="text-[10px] font-bold text-[#0075ff] w-6">{allocationWeights[addr] || "50"}%</span>
                                                                </div>
                                                            </>
                                                        )}
                                                        <span className="w-1 h-1 bg-white/10 rounded-full" />
                                                        {isTerminated ? (
                                                            <span className="text-rose-500 text-[9px] font-black uppercase tracking-widest">Permanently Terminated</span>
                                                        ) : (
                                                            <button
                                                                onClick={() => toggleWalletTracking(addr)}
                                                                className={`text-[9px] font-black uppercase tracking-widest transition-colors ${isDisabled ? 'text-white/40 hover:text-white' : 'text-white/60 hover:text-white'}`}
                                                            >
                                                                {isDisabled ? '[ Resume Tracking ]' : '[ Hibernate Node ]'}
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-4 shrink-0 pl-4">
                                                <div className="hidden sm:flex flex-col items-end mr-4">
                                                    <p className="text-[9px] font-black text-white/10 uppercase tracking-widest">Protocol</p>
                                                    <p className="text-[10px] font-black text-white/40 uppercase">v2.4.0</p>
                                                </div>
                                                {!isTerminated && (
                                                    <button onClick={() => terminateWallet(addr)} className="text-white/5 hover:text-rose-500 transition-colors p-2 rounded-lg hover:bg-white/5" title="Terminate Node">
                                                        <Icons.Trash />
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                                {wallets.length === 0 && (
                                    <div className="py-24 text-center border border-dashed border-white/10 rounded-xl">
                                        <p className="text-[11px] font-black uppercase text-white/10 tracking-[0.4em] italic">Cluster currently offline</p>
                                    </div>
                                )}
                            </div>
                        </section>
                    </div>
                )}

                {activeTab === "REPLICATION" && (
                    <div className="animate-in fade-in zoom-in-95 duration-500">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
                            <div>
                                <h1 className="text-[32px] font-black uppercase tracking-tight leading-none mb-2">Replication Intake</h1>
                                <p className="text-white/30 text-[12px] font-bold tracking-widest uppercase italic flex items-center gap-2">
                                    Sub-second trade capture & verification stream
                                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#01b574]/20 border border-[#01b574]/30 text-[9px] font-black text-[#01b574] uppercase tracking-wider">
                                        <span className="w-1.5 h-1.5 rounded-full bg-[#01b574] animate-pulse" /> Live
                                    </span>
                                </p>
                            </div>

                            {/* Stream Analytics Dashboard */}
                            <div className="flex gap-4 lg:gap-8">
                                <div className="bg-white/5 border border-white/10 px-6 py-4 rounded-xl">
                                    <p className="text-[9px] font-black text-white/20 uppercase tracking-[0.2em] mb-1">Total PNL</p>
                                    <p className={`text-[18px] font-black tabular-nums ${stats.balance - stats.initial_balance >= 0 ? 'text-[#01b574]' : 'text-rose-500'}`}>
                                        {stats.balance - stats.initial_balance >= 0 ? '+' : ''}${(stats.balance - stats.initial_balance).toFixed(2)}
                                    </p>
                                </div>
                                <div className="bg-white/5 border border-white/10 px-6 py-4 rounded-xl">
                                    <p className="text-[9px] font-black text-white/20 uppercase tracking-[0.2em] mb-1">New Balance</p>
                                    <p className="text-[18px] font-black text-white tabular-nums">${stats.balance.toFixed(2)}</p>
                                </div>
                                <div className="bg-white/5 border border-white/10 px-6 py-4 rounded-xl">
                                    <p className="text-[9px] font-black text-white/20 uppercase tracking-[0.2em] mb-1">Executed Volume</p>
                                    <p className="text-[18px] font-black text-[#0075ff] tabular-nums">
                                        ${trades.reduce((acc, t) => acc + (t.total || (t.amount * t.price)), 0).toFixed(2)}
                                    </p>
                                </div>
                            </div>

                            <div className="flex items-center gap-4">
                                <div className="relative group">
                                    <select
                                        value={searchAddress}
                                        onChange={(e) => setSearchAddress(e.target.value)}
                                        className="appearance-none bg-black border border-white/10 px-6 py-3.5 pr-12 rounded-xl text-[11px] font-black uppercase tracking-widest text-white outline-none focus:border-white transition-all cursor-pointer"
                                    >
                                        <option value="">All Source Addresses</option>
                                        {wallets.map(w => (
                                            <option key={w} value={w}>{w.substring(0, 10)}...</option>
                                        ))}
                                    </select>
                                    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-white/20 group-hover:text-white transition-colors">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M6 9l6 6 6-6" /></svg>
                                    </div>
                                </div>

                                <div className="flex bg-white/5 border border-white/10 p-1 rounded-xl">
                                    {["ALL", "BUY", "SELL"].map((side) => (
                                        <button
                                            key={side}
                                            onClick={() => setSideFilter(side as any)}
                                            className={`px-6 py-2.5 rounded-lg text-[10px] font-black tracking-widest transition-all ${sideFilter === side ? 'bg-white text-black shadow-lg scale-105' : 'text-white/30 hover:text-white'}`}
                                        >
                                            {side}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="bg-black border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="border-b border-white/10 bg-white/[0.02]">
                                        <th className="px-8 py-6 text-[10px] font-black text-white/20 uppercase tracking-[0.2em] w-16">#</th>
                                        <th className="px-8 py-6 text-[10px] font-black text-white/20 uppercase tracking-[0.2em]">Market</th>
                                        <th className="px-8 py-6 text-[10px] font-black text-white/20 uppercase tracking-[0.2em]">Side</th>
                                        <th className="px-8 py-6 text-[10px] font-black text-white/20 uppercase tracking-[0.2em] text-right">Amount</th>
                                        <th className="px-8 py-6 text-[10px] font-black text-white/20 uppercase tracking-[0.2em] text-right">Price</th>
                                        <th className="px-8 py-6 text-[10px] font-black text-white/20 uppercase tracking-[0.2em] text-right">Total</th>
                                        <th className="px-8 py-6 text-[10px] font-black text-white/20 uppercase tracking-[0.2em] text-right">Wallet</th>
                                    </tr>
                                </thead>
                                <Reorder.Group axis="y" values={trades} onReorder={setTrades} as="tbody" className="contents">
                                    {filteredTrades.map((trade, index) => (
                                        <Reorder.Item
                                            key={trade.id || index}
                                            value={trade}
                                            as="tr"
                                            className="hover:bg-white/[0.05] transition-colors group cursor-grab active:cursor-grabbing relative border-b border-white/[0.05] last:border-0"
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, scale: 0.95 }}
                                            whileDrag={{ backgroundColor: 'rgba(255, 255, 255, 0.05)', backdropFilter: 'blur(10px)', zIndex: 10, border: '1px solid rgba(255,255,255,0.2)' }}
                                        >
                                            <td className="px-8 py-5 text-[11px] font-black text-white/10 tabular-nums">{(index + 1).toString().padStart(2, '0')}</td>
                                            <td className="px-8 py-5">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-2 h-2 rounded-full bg-white/20 group-hover:bg-white transition-colors" />
                                                    <span className="text-[13px] font-black text-white tracking-tight">{trade.market}</span>
                                                </div>
                                            </td>
                                            <td className="px-8 py-5">
                                                <span className={`px-2.5 py-1 rounded text-[9px] font-black ${trade.side === "BUY" ? "bg-white text-black" : "border border-white/20 text-white/60"}`}>
                                                    {trade.side}
                                                </span>
                                            </td>
                                            <td className="px-8 py-5 text-[13px] font-bold text-white/80 text-right tabular-nums">{trade.amount.toLocaleString()}</td>
                                            <td className="px-8 py-5 text-[13px] font-bold text-white/80 text-right tabular-nums">${trade.price.toFixed(4)}</td>
                                            <td className="px-8 py-5 text-[13px] font-black text-white text-right tabular-nums">${trade.total ? trade.total.toFixed(2) : (trade.amount * trade.price).toFixed(2)}</td>
                                            <td className="px-8 py-5 text-right">
                                                <span className="text-[11px] font-mono text-white/30 group-hover:text-white/60 transition-colors uppercase">{trade.wallet ? `${trade.wallet.substring(0, 6)}...${trade.wallet.substring(38)}` : 'UNKNOWN'}</span>
                                            </td>
                                        </Reorder.Item>
                                    ))}
                                </Reorder.Group>
                            </table>
                            {filteredTrades.length === 0 && (
                                <div className="py-32 flex flex-col items-center justify-center">
                                    <div className="w-16 h-16 border-2 border-dashed border-white/10 rounded-full flex items-center justify-center mb-6 animate-pulse">
                                        <Icons.Matrix />
                                    </div>
                                    <p className="text-[11px] font-black uppercase text-white/10 tracking-[0.4em] italic mb-2">No packets detected</p>
                                    <p className="text-[9px] text-white/5 font-bold uppercase tracking-widest">Awaiting sub-second frequency injection</p>
                                </div>
                            )}
                        </div>
                        <div className="mt-6 flex items-center justify-center gap-3">
                            <span className="w-1 h-1 bg-white/20 rounded-full" />
                            <p className="text-[10px] text-white/20 font-bold uppercase tracking-widest">Drag rows to prioritize execution sequence</p>
                            <span className="w-1 h-1 bg-white/20 rounded-full" />
                        </div>
                    </div >
                )}
                {/* Phase 3 features hidden in Phase 1 release */}
                {/* {activeTab === "STRATEGY" && (
                    <div className="animate-in fade-in zoom-in-95 duration-500 max-w-6xl mx-auto">
                        <div className="text-center mb-16">
                            <h1 className="text-[32px] font-black uppercase tracking-tighter mb-2 italic">Institutional Alpha Dashboard</h1>
                            <p className="text-white/30 text-[12px] font-bold tracking-[0.3em] uppercase italic">AI Portfolio & Logic Constraints</p>
                        </div>

                        <div className="mb-12 bg-[#0075ff]/5 border border-[#0075ff]/20 rounded-3xl p-10 relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-10 opacity-10">
                                <Icons.Strategy />
                            </div>
                            <div className="relative z-10">
                                <div className="flex items-center justify-between mb-8">
                                    <div>
                                        <h2 className="text-[20px] font-black uppercase italic tracking-tight mb-1">Institutional Alpha Portfolio</h2>
                                        <p className="text-[11px] text-[#0075ff] font-black uppercase tracking-[0.2em]">Automated Selection • Conviction Weighted</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-[10px] font-black text-white/30 uppercase tracking-widest mb-1">Total Conviction</p>
                                        <p className="text-[24px] font-black text-white">{(aiPortfolio?.total_conviction || 0).toFixed(2)}</p>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                                    {aiPortfolio?.top_assets?.map((asset: any, i: number) => (
                                        <div key={i} className="bg-black/40 border border-white/10 p-5 rounded-2xl hover:border-[#0075ff]/50 transition-all group">
                                            <div className="flex items-center justify-between mb-4">
                                                <span className="text-[20px] font-black text-[#0075ff]">0{i + 1}</span>
                                                <span className="text-[10px] font-black text-white group-hover:text-[#0075ff] transition-colors">{asset.allocation}%</span>
                                            </div>
                                            <p className="text-[13px] font-black text-white truncate mb-1 uppercase">{asset.market}</p>
                                            <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden mt-3">
                                                <div className="h-full bg-[#0075ff] transition-all duration-1000" style={{ width: `${asset.allocation}%` }} />
                                            </div>
                                        </div>
                                    )) || (
                                            <div className="col-span-5 py-12 text-center text-white/10 font-bold uppercase italic tracking-widest">
                                                {isAuthenticated && (stats as any).subscriptionStatus !== 'free' ? 'Constructing Portfolio...' : 'Requires Pro/Elite Authorization'}
                                            </div>
                                        )}
                                </div>
                                {(stats as any).subscriptionStatus === 'free' && (
                                    <div className="mt-8 flex justify-center">
                                        <button onClick={() => setActiveTab("SUBSCRIPTION")} className="px-8 py-3 bg-[#0075ff] text-white font-black text-[10px] tracking-[0.2em] uppercase rounded-xl hover:bg-[#0075ff]/80 transition-all">Unlock Institutional Alpha</button>
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            <section className="bg-black border border-white/10 p-8 rounded-xl shadow-xl space-y-8">
                                <div className="space-y-4">
                                    <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/20">Class Registry</p>
                                    <select
                                        onChange={(e) => { if (e.target.value) { addFilter(e.target.value); e.target.value = ""; } }}
                                        className="w-full bg-white/5 border border-white/10 rounded-xl px-5 py-4 text-[14px] font-bold text-white outline-none focus:border-white transition-all"
                                    >
                                        <option value="" disabled selected>Inject directive...</option>
                                        {availableCategories.filter(cat => !filters.includes(cat.toLowerCase())).map(cat => (
                                            <option key={cat} value={cat}>{cat}</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="space-y-4 pt-4 border-t border-white/5">
                                    <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/20">Manual Logic Injection</p>
                                    <div className="flex gap-3">
                                        <input
                                            value={newFilter}
                                            onChange={(e) => setNewFilter(e.target.value)}
                                            placeholder="Signal Type..."
                                            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-5 py-4 text-[14px] font-bold outline-none focus:border-white transition-all text-white placeholder:text-white/20"
                                        />
                                        <button onClick={() => addFilter()} className="bg-white text-black px-8 rounded-xl font-black text-[11px] uppercase tracking-widest transition-all hover:bg-white/90 active:scale-95">Inject</button>
                                    </div>
                                </div>
                            </section>

                            <section className="bg-white/[0.01] border border-white/5 p-8 rounded-xl flex flex-col min-h-[300px]">
                                <div className="flex items-center justify-between mb-8">
                                    <h3 className="text-[14px] font-black text-white uppercase tracking-widest italic">Active Constraints</h3>
                                    <span className="text-white/10 text-[9px] font-black tracking-widest uppercase">{filters.length} rules</span>
                                </div>

                                <div className="flex flex-wrap gap-2.5 content-start">
                                    {filters.map((cat) => (
                                        <div key={cat} className="bg-white/5 border border-white/10 pl-4 pr-1.5 py-2.5 rounded-lg flex items-center gap-4 hover:border-white/30 transition-all cursor-default group border-l-2 border-l-white">
                                            <span className="text-[11px] font-black text-white/60 uppercase tracking-tighter">{cat}</span>
                                            <button onClick={() => removeFilter(cat)} className="text-white/10 hover:text-white transition-all p-1 opacity-0 group-hover:opacity-100">
                                                <Icons.Trash />
                                            </button>
                                        </div>
                                    ))}
                                    {filters.length === 0 && (
                                        <div className="flex-1 flex flex-col items-center justify-center opacity-10">
                                            <p className="text-[10px] font-black italic uppercase tracking-[0.4em]">Zero Override</p>
                                        </div>
                                    )}
                                </div>
                            </section>
                        </div>
                    </div>
                )} */}

                {activeTab === "SETTINGS" && (
                    <div className="animate-in fade-in zoom-in-95 duration-500 max-w-2xl mx-auto">
                        <div className="mb-10 text-center">
                            <h1 className="text-[32px] font-black uppercase tracking-tighter mb-2">Platform Configuration</h1>
                            <p className="text-white/30 text-[12px] font-bold tracking-widest uppercase italic">Institutional grade system parameters</p>
                        </div>

                        <div className="bg-black border border-white/10 p-10 rounded-xl shadow-2xl space-y-12">
                            {/* Section 1: Execution Algorithm */}
                            <div className="space-y-8">
                                <h3 className="text-[14px] font-black uppercase text-white/60 tracking-[0.2em] border-b border-white/5 pb-2">Execution Algorithm</h3>
                                <div className="space-y-4">
                                    <label className="block text-[11px] font-black uppercase text-white/40 tracking-widest">Execution Threshold (Min Balance)</label>
                                    <div className="flex gap-4">
                                        <div className="relative flex-1">
                                            <span className="absolute left-6 top-1/2 -translate-y-1/2 text-white/40 font-bold">$</span>
                                            <input
                                                type="text"
                                                value={balanceThreshold}
                                                onChange={(e) => setBalanceThreshold(e.target.value)}
                                                className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-6 py-5 text-[16px] font-black outline-none focus:border-white focus:bg-white/10 transition-all text-white placeholder:text-white/10"
                                                placeholder="0.00"
                                            />
                                        </div>
                                        <button
                                            onClick={handleUpdateBalanceThreshold}
                                            className="px-8 bg-white text-black rounded-xl font-black text-[11px] uppercase tracking-widest transition-all hover:bg-white/90 active:scale-95 whitespace-nowrap"
                                        >
                                            Set Threshold
                                        </button>
                                    </div>
                                    <p className="text-[10px] text-white/20 font-bold italic uppercase tracking-wider">Engine will skip all trade replication if balance falls below this amount.</p>
                                </div>

                                <div className="space-y-4">
                                    <label className="block text-[11px] font-black uppercase text-white/40 tracking-widest">Paper Trading Initialization</label>
                                    <div className="flex gap-4">
                                        <div className="relative flex-1">
                                            <span className="absolute left-6 top-1/2 -translate-y-1/2 text-white/40 font-bold">$</span>
                                            <input
                                                type="text"
                                                value={initialBalanceInput}
                                                onChange={(e) => setInitialBalanceInput(e.target.value)}
                                                className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-6 py-5 text-[16px] font-black outline-none focus:border-white focus:bg-white/10 transition-all text-white placeholder:text-white/10"
                                                placeholder="100.00"
                                            />
                                        </div>
                                        <button
                                            onClick={handleUpdateInitialBalance}
                                            className="px-8 bg-white text-black rounded-xl font-black text-[11px] uppercase tracking-widest transition-all hover:bg-white/90 active:scale-95 whitespace-nowrap"
                                        >
                                            Apply Capital
                                        </button>
                                    </div>
                                    <p className="text-[10px] text-white/20 font-bold italic uppercase tracking-wider">Initial simulation balance used for performance delta calculations.</p>
                                </div>
                            </div>

                            {/* Section 2: Market Intelligence */}
                            <div className="space-y-8 pt-8 border-t border-white/5">
                                <h3 className="text-[14px] font-black uppercase text-white/60 tracking-[0.2em] border-b border-white/5 pb-2">Market Intelligence</h3>
                                <div className="space-y-4">
                                    <label className="block text-[11px] font-black uppercase text-white/40 tracking-widest">Alpha P&L Threshold (Daily)</label>
                                    <div className="flex gap-4">
                                        <div className="relative flex-1">
                                            <span className="absolute left-6 top-1/2 -translate-y-1/2 text-white/40 font-bold">$</span>
                                            <input
                                                type="text"
                                                value={dailyPnlThreshold}
                                                onChange={(e) => setDailyPnlThreshold(e.target.value)}
                                                className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-6 py-5 text-[16px] font-black outline-none focus:border-white focus:bg-white/10 transition-all text-white placeholder:text-white/10"
                                                placeholder="1000.00"
                                            />
                                        </div>
                                        <button
                                            onClick={handleUpdateDailyPnlThreshold}
                                            className="px-8 bg-white text-black rounded-xl font-black text-[11px] uppercase tracking-widest transition-all hover:bg-white/90 active:scale-95 whitespace-nowrap"
                                        >
                                            Set Alpha Filter
                                        </button>
                                    </div>
                                    <p className="text-[10px] text-white/20 font-bold italic uppercase tracking-wider">Only traders with a daily P&L above this amount will appear in your dashboard Intel.</p>
                                </div>
                            </div>

                            {/* Section 3: Trading Configuration */}
                            <div className="space-y-8 pt-8 border-t border-white/5">
                                <h3 className="text-[14px] font-black uppercase text-white/60 tracking-[0.2em] border-b border-white/5 pb-2">Trading Configuration</h3>
                                <div className="grid grid-cols-2 gap-4">
                                    <button
                                        onClick={() => handleUpdateTradingMode("paper")}
                                        className={`flex flex-col items-center justify-center p-6 rounded-2xl border transition-all ${tradingMode === "paper" ? "bg-[#0075ff]/10 border-[#0075ff] shadow-[0_0_20px_rgba(0,117,255,0.2)]" : "bg-white/5 border-white/10 hover:border-white/20"}`}
                                    >
                                        <span className="text-2xl mb-2">📄</span>
                                        <span className="text-[11px] font-black uppercase tracking-widest text-white">Paper Trading</span>
                                        <span className="text-[9px] text-white/40 font-bold mt-1 uppercase italic">Simulated Execution</span>
                                    </button>
                                    <button
                                        onClick={() => handleUpdateTradingMode("live")}
                                        className={`flex flex-col items-center justify-center p-6 rounded-2xl border transition-all ${tradingMode === "live" ? "bg-[#01b574]/10 border-[#01b574] shadow-[0_0_20px_rgba(1,181,116,0.2)]" : "bg-white/5 border-white/10 hover:border-white/20"}`}
                                    >
                                        <span className="text-2xl mb-2">⚡</span>
                                        <span className="text-[11px] font-black uppercase tracking-widest text-white">Live Trading</span>
                                        <span className="text-[9px] text-white/40 font-bold mt-1 uppercase italic">Institutional Rails</span>
                                    </button>
                                </div>
                                {tradingMode === "live" && (
                                    <div className="space-y-4 animate-in slide-in-from-top-6">
                                        <label className="block text-[11px] font-black uppercase text-white/40 tracking-widest">Connect Polymarket Address</label>
                                        <div className="flex gap-4">
                                            <input
                                                type="text"
                                                value={livePolymarketAddress}
                                                onChange={(e) => setLivePolymarketAddress(e.target.value)}
                                                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-6 py-4 text-[13px] font-bold outline-none focus:border-white transition-all text-white font-mono"
                                                placeholder="0x..."
                                            />
                                            <button
                                                onClick={handleUpdatePolymarketAddress}
                                                className="px-6 bg-[#01b574] text-white rounded-xl font-black text-[10px] uppercase tracking-widest transition-all hover:bg-[#01b574]/80"
                                            >
                                                Connect
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )
                }
            </div >

            <style jsx global>{`
                @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800;900&display=swap');
                
                body {
                    font-family: 'Inter', 'Plus Jakarta Sans', sans-serif;
                    background-color: #050505;
                    color: white;
                    margin: 0;
                    -webkit-font-smoothing: antialiased;
                }

                .custom-scrollbar::-webkit-scrollbar {
                    width: 4px;
                }
                .custom-scrollbar::-webkit-scrollbar-track {
                    background: transparent;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 10px;
                }

                .animate-in {
                    animation-duration: 0.4s;
                    animation-fill-mode: both;
                    animation-timing-function: cubic-bezier(0.16, 1, 0.3, 1);
                }
                
                @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
                @keyframes zoom-in-95 { from { transform: scale(0.99); opacity: 0; } to { transform: scale(1); opacity: 1; } }
                @keyframes slide-in-from-bottom-4 { from { transform: translateY(15px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
                @keyframes slide-in-from-right-4 { from { transform: translateX(15px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
                @keyframes slide-in-from-top-6 { from { transform: translateY(-20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

                .fade-in { animation-name: fade-in; }
                .zoom-in-95 { animation-name: zoom-in-95; }
                .slide-in-from-bottom-4 { animation-name: slide-in-from-bottom-4; }
                .slide-in-from-right-4 { animation-name: slide-in-from-right-4; }
                .slide-in-from-top-6 { animation-name: slide-in-from-top-6; }
            `}</style>
        </main >
    );
}
