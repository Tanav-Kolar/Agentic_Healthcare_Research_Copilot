import React, { useState } from 'react';
import { Quote, Sparkles, ExternalLink, Clock, FileText } from 'lucide-react';

const EvidencePanel = ({ quotes, recentChanges }) => {
    const [activeTab, setActiveTab] = useState('citations');

    return (
        <div className="right-sidebar glass-panel flex flex-col overflow-hidden animate-fade-in">
            <div className="flex border-b border-white/5">
                <button
                    onClick={() => setActiveTab('citations')}
                    className={`flex-1 py-4 text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-colors ${activeTab === 'citations' ? 'text-accent-primary border-b-2 border-accent-primary' : 'text-text-secondary hover:text-text-primary'
                        }`}
                >
                    <Quote size={14} /> Citations
                </button>
                <button
                    onClick={() => setActiveTab('recent')}
                    className={`flex-1 py-4 text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-colors ${activeTab === 'recent' ? 'text-accent-primary border-b-2 border-accent-primary' : 'text-text-secondary hover:text-text-primary'
                        }`}
                >
                    <Sparkles size={14} /> What Changed
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
                {activeTab === 'citations' ? (
                    <div className="flex flex-col gap-4">
                        {quotes.length === 0 ? (
                            <div className="text-center py-20 opacity-30">
                                <FileText size={48} className="mx-auto mb-2" />
                                <p className="text-sm">No citations selected.</p>
                            </div>
                        ) : (
                            quotes.map((q, idx) => (
                                <div key={idx} className="glass-card p-4 text-sm animate-fade-in">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="bg-accent-soft text-accent-primary px-2 py-0.5 rounded text-[10px] font-bold">
                                            SOURCE [{q.id}]
                                        </span>
                                        {q.pmid && (
                                            <a
                                                href={`https://pubmed.ncbi.nlm.nih.gov/${q.pmid}`}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="text-text-secondary hover:text-accent-primary transition-colors"
                                            >
                                                <ExternalLink size={12} />
                                            </a>
                                        )}
                                    </div>
                                    <p className="text-text-primary italic font-serif leading-relaxed">
                                        "{q.quote}"
                                    </p>
                                </div>
                            ))
                        )}
                    </div>
                ) : (
                    <div className="flex flex-col gap-4">
                        <div className="bg-accent-soft/30 p-3 rounded-lg border border-accent-soft mb-2">
                            <p className="text-[10px] text-accent-primary font-bold uppercase mb-1">Impact Analysis</p>
                            <p className="text-xs text-text-primary leading-tight">
                                Showing breakthrough research and guideline updates from the last 24 months.
                            </p>
                        </div>
                        {recentChanges.length === 0 ? (
                            <div className="text-center py-20 opacity-30">
                                <Clock size={48} className="mx-auto mb-2" />
                                <p className="text-sm">No recent updates found.</p>
                            </div>
                        ) : (
                            recentChanges.map((item, idx) => (
                                <div key={idx} className="glass-card p-4 animate-fade-in border-l-2 border-accent-primary">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-[10px] text-accent-primary font-bold uppercase">{item.year}</span>
                                        <span className="text-[10px] text-text-secondary">•</span>
                                        <span className="text-[10px] text-text-secondary uppercase">PubMed</span>
                                    </div>
                                    <h4 className="text-xs font-semibold text-text-primary mb-2 line-clamp-2">
                                        {item.summary}
                                    </h4>
                                    <div className="flex justify-end">
                                        <a
                                            href={item.pmid ? `https://pubmed.ncbi.nlm.nih.gov/${item.pmid}` : item.doi ? `https://doi.org/${item.doi}` : '#'}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="text-[10px] text-accent-primary hover:underline flex items-center gap-1"
                                        >
                                            View Source <ExternalLink size={8} />
                                        </a>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default EvidencePanel;
