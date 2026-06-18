import React, { useEffect, useState } from 'react';
import { Database, Shield, Globe, Terminal, RefreshCw, ArrowRight } from 'lucide-react';

interface Stats {
  dbOnline: boolean;
  totalIOCs: number;
  feedCount: number;
}

export default function App() {
  const [stats, setStats] = useState<Stats>({ dbOnline: false, totalIOCs: 0, feedCount: 0 });

  useEffect(() => {
    async function fetchStats() {
      try {
        const [healthRes, feedsRes, iocRes] = await Promise.all([
          fetch('/api/v1/health').then(r => r.json()),
          fetch('/api/v1/feeds').then(r => r.json()),
          fetch('/api/v1/indicators?limit=1').then(r => r.json()),
        ]);
        setStats({
          dbOnline: healthRes.status === 'healthy',
          totalIOCs: iocRes.total || 0,
          feedCount: feedsRes.feeds?.length || 0,
        });
      } catch {
        setStats(s => ({ ...s, dbOnline: false }));
      }
    }
    fetchStats();
  }, []);

  return (
    <div className="min-h-screen bg-[#0c0c0c] text-neutral-300 font-sans">
      <div className="max-w-5xl mx-auto px-6 py-12">
        {/* Hero */}
        <header className="mb-14 border-b border-neutral-800 pb-10">
          <div className="flex items-center gap-3 mb-4">
            <Shield className="w-9 h-9 text-neutral-100" />
            <h1 className="text-3xl font-medium tracking-wide text-neutral-100">DeepTrawl</h1>
          </div>
          <p className="text-neutral-500 text-base max-w-2xl leading-relaxed">
            Deep web leak search. Fetches threat intelligence feeds through Tor, extracts
            indicators of compromise, and stores them with cryptographic deduplication.
          </p>
          <div className="flex gap-3 mt-5">
            <a href="/dashboard" className="inline-flex items-center gap-2 bg-neutral-800 border border-neutral-700 hover:bg-neutral-700 text-neutral-200 px-5 py-2 rounded text-sm transition-colors">
              Open Dashboard <ArrowRight className="w-4 h-4" />
            </a>
            <a href="/api/v1/health" className="inline-flex items-center gap-2 bg-neutral-900 border border-neutral-800 hover:bg-neutral-800 text-neutral-400 px-5 py-2 rounded text-sm transition-colors">
              API Status
            </a>
          </div>
        </header>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-12">
          <div className="bg-[#121212] border border-neutral-800 rounded p-5">
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-4 h-4 text-neutral-400" />
              <h3 className="text-xs text-neutral-500 uppercase tracking-wider">Database</h3>
            </div>
            <p className={`text-lg font-medium ${stats.dbOnline ? 'text-green-400' : 'text-red-400'}`}>
              {stats.dbOnline ? 'Online' : 'Offline'}
            </p>
          </div>
          <div className="bg-[#121212] border border-neutral-800 rounded p-5">
            <div className="flex items-center gap-2 mb-2">
              <Terminal className="w-4 h-4 text-neutral-400" />
              <h3 className="text-xs text-neutral-500 uppercase tracking-wider">IOCs Collected</h3>
            </div>
            <p className="text-lg font-medium text-neutral-200">{stats.totalIOCs.toLocaleString()}</p>
          </div>
          <div className="bg-[#121212] border border-neutral-800 rounded p-5">
            <div className="flex items-center gap-2 mb-2">
              <Globe className="w-4 h-4 text-neutral-400" />
              <h3 className="text-xs text-neutral-500 uppercase tracking-wider">Active Feeds</h3>
            </div>
            <p className="text-lg font-medium text-neutral-200">{stats.feedCount}</p>
          </div>
        </div>

        {/* What it does */}
        <section className="grid gap-6 md:grid-cols-2 mb-12">
          <div className="bg-[#121212] border border-neutral-800 rounded p-6">
            <div className="flex items-center gap-2 mb-3 text-neutral-200">
              <Globe className="w-4 h-4" />
              <h2 className="font-medium text-sm tracking-wide uppercase">Tor-Routed Collection</h2>
            </div>
            <p className="text-neutral-500 text-sm leading-relaxed">
              All feed requests are proxied through Tor SOCKS5. When rate-limited, the
              engine automatically rotates the Tor circuit for a fresh exit node.
            </p>
          </div>
          <div className="bg-[#121212] border border-neutral-800 rounded p-6">
            <div className="flex items-center gap-2 mb-3 text-neutral-200">
              <Shield className="w-4 h-4" />
              <h2 className="font-medium text-sm tracking-wide uppercase">IOC Extraction</h2>
            </div>
            <p className="text-neutral-500 text-sm leading-relaxed">
              Deterministic regex scanning extracts IPv4 addresses, domains, email addresses,
              MD5/SHA256 hashes, and BTC/XMR wallet addresses from raw feed data.
            </p>
          </div>
          <div className="bg-[#121212] border border-neutral-800 rounded p-6">
            <div className="flex items-center gap-2 mb-3 text-neutral-200">
              <RefreshCw className="w-4 h-4" />
              <h2 className="font-medium text-sm tracking-wide uppercase">Auto-Collection</h2>
            </div>
            <p className="text-neutral-500 text-sm leading-relaxed">
              Background task runs every 60 minutes. Manual triggers available via the
              dashboard or API endpoint.
            </p>
          </div>
          <div className="bg-[#121212] border border-neutral-800 rounded p-6">
            <div className="flex items-center gap-2 mb-3 text-neutral-200">
              <Database className="w-4 h-4" />
              <h2 className="font-medium text-sm tracking-wide uppercase">Deduplication</h2>
            </div>
            <p className="text-neutral-500 text-sm leading-relaxed">
              Every IOC is SHA-256 hashed before insertion. Duplicate entries from
              overlapping feeds are silently skipped at the database level.
            </p>
          </div>
        </section>

        {/* Architecture */}
        <section className="mb-12">
          <h3 className="text-xs tracking-widest font-medium text-neutral-500 uppercase mb-4">Project Structure</h3>
          <div className="space-y-2 font-mono text-sm">
            {[
              ['app/core/collector.py', 'Async HTTP engine — Tor SOCKS5 proxy + auto-retry'],
              ['app/core/extractor.py', 'Regex patterns: IPv4, domains, emails, hashes, wallets'],
              ['app/core/identity_manager.py', 'Tor ControlPort integration — circuit rotation'],
              ['app/database.py', 'PostgreSQL via asyncpg — schema + connection pool'],
              ['app/main.py', 'FastAPI app — REST API + Jinja2 dashboard'],
              ['docker-compose.yml', 'Full Docker stack: app + Tor + PostgreSQL'],
            ].map(([file, desc]) => (
              <div key={file} className="flex flex-col sm:flex-row sm:justify-between p-3 bg-neutral-900 border border-neutral-800 rounded gap-1">
                <code className="text-neutral-300">{file}</code>
                <span className="text-neutral-500 text-xs">{desc}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Footer */}
        <footer className="pt-8 border-t border-neutral-800 text-xs text-neutral-600 text-center space-y-1">
          <p>DeepTrawl — deep web leak search. Runs at <code className="text-neutral-500">/dashboard</code>.</p>
          <p>API docs at <a href="/docs" className="text-neutral-500 hover:text-neutral-400 underline">/docs</a> (FastAPI Swagger).</p>
        </footer>
      </div>
    </div>
  );
}
