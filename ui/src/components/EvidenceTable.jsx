import React from 'react';
import { ExternalLink, Info, Award } from 'lucide-react';

const EvidenceTable = ({ evidence }) => {
    if (!evidence || evidence.length === 0) return null;

    return (
        <div className="mt-8 animate-fade-in">
            <div className="flex items-center gap-2 mb-4">
                <Award className="text-accent-primary" size={20} />
                <h3 className="text-lg font-bold">Evidence Synthesis Table</h3>
            </div>
            <div className="glass-panel overflow-hidden border border-white/5 rounded-xl">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-white/5 border-b border-white/5">
                                <th className="px-4 py-3 text-[10px] font-bold uppercase text-text-secondary tracking-widest">Study</th>
                                <th className="px-4 py-3 text-[10px] font-bold uppercase text-text-secondary tracking-widest">Design</th>
                                <th className="px-4 py-3 text-[10px] font-bold uppercase text-text-secondary tracking-widest">Year</th>
                                <th className="px-4 py-3 text-[10px] font-bold uppercase text-text-secondary tracking-widest">Journal</th>
                                <th className="px-4 py-3 text-[10px] font-bold uppercase text-text-secondary tracking-widest">DOI/Link</th>
                            </tr>
                        </thead>
                        <tbody>
                            {evidence.map((item, idx) => (
                                <tr key={idx} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                                    <td className="px-4 py-4 max-w-xs">
                                        <p className="text-xs font-semibold text-text-primary line-clamp-2 leading-snug">
                                            {item.title}
                                        </p>
                                    </td>
                                    <td className="px-4 py-4">
                                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${item.type === 'RCT' ? 'bg-green-500/20 text-green-400' :
                                                item.type === 'Meta-analysis' ? 'bg-blue-500/20 text-blue-400' :
                                                    'bg-slate-500/20 text-slate-400'
                                            }`}>
                                            {item.type}
                                        </span>
                                    </td>
                                    <td className="px-4 py-4 text-xs text-text-secondary font-mono">
                                        {item.year}
                                    </td>
                                    <td className="px-4 py-4">
                                        <p className="text-[10px] text-text-secondary italic">
                                            {item.journal}
                                        </p>
                                    </td>
                                    <td className="px-4 py-4">
                                        <div className="flex gap-2">
                                            <a
                                                href={item.source_url || `https://pubmed.ncbi.nlm.nih.gov/${item.pmid}`}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="p-1.5 rounded-lg bg-white/5 text-text-secondary hover:text-accent-primary transition-colors"
                                                title="View source"
                                            >
                                                <ExternalLink size={14} />
                                            </a>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default EvidenceTable;
